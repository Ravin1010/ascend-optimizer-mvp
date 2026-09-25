// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Address} from "@openzeppelin/contracts/utils/Address.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {
    IW0G,
    IV3Factory,
    IV3Pool,
    IV3PeripheryMetadata,
    IV3PositionManager,
    IV3SwapRouterV1,
    IV3SwapRouter02
} from "../interfaces/IV3Liquidity.sol";
import {IStrategyAdapter} from "../interfaces/IStrategyAdapter.sol";
import {V3PositionMath} from "../libraries/V3PositionMath.sol";

/// @title V3LiquidityAdapter
/// @notice Shared W0G/USDC.e concentrated-liquidity adapter for Jaine and
///         canonical Uniswap V3 deployments on 0G.
/// @dev Deployment is fixed to one factory/router/NPM/pool/fee/range.
///
///      Vault share units are internal pooled liquidity units. The first
///      deposit mints shares equal to V3 liquidity; later deposits mint shares
///      pro rata to the increase in position liquidity.
///
///      LP trading fees are intentionally left embedded in the NFT position
///      until withdrawal/harvest logic is added. This first MVP implementation
///      therefore values principal from active liquidity only and does not
///      double count fee growth through RewardAccounting.
///
///      Entry/exit swap protections are supplied as bounded ABI-encoded data:
///      deposit: abi.encode(minSwapOutUSDC, minAmount0, minAmount1, deadline)
///      withdraw: abi.encode(minSwapOutW0G, amount0Min, amount1Min, deadline)
contract V3LiquidityAdapter is IStrategyAdapter, ReentrancyGuard {
    using Address for address payable;
    using SafeERC20 for IERC20;
    using SafeERC20 for IW0G;

    enum RouterMode {
        V1,
        ROUTER02
    }

    uint256 public constant BPS_DENOMINATOR = 10_000;

    address public immutable vault;
    IV3Factory public immutable factory;
    address public immutable router;
    IV3PositionManager public immutable positionManager;
    IV3Pool public immutable pool;
    IW0G public immutable w0g;
    IERC20 public immutable usdce;
    uint24 public immutable feeTier;
    int24 public immutable tickLower;
    int24 public immutable tickUpper;
    uint160 public immutable sqrtLowerX96;
    uint160 public immutable sqrtUpperX96;
    RouterMode public immutable routerMode;

    uint256 public tokenId;
    uint256 public totalStrategyShares;

    error ZeroVault();
    error InvalidContract(address target);
    error InvalidPool(address expected, address actual);
    error PoolMetadataMismatch();
    error PeripheryFactoryMismatch(address expected, address actual);
    error InvalidTicks(int24 lower, int24 upper);
    error InvalidSqrtBounds(uint160 lower, uint160 upper);
    error OnlyVault(address caller);
    error ZeroAmount();
    error ZeroMinShares();
    error ZeroMinAmountOut();
    error InvalidNativeValue(uint256 expected, uint256 received);
    error InvalidExecutionData();
    error AllocationExpired(uint256 deadline, uint256 nowTs);
    error InvalidPositionTokenId(uint256 expected, uint256 actual);
    error InsufficientShares(uint256 minimum, uint256 received);
    error InsufficientStrategyShares(uint256 available, uint256 requested);
    error ZeroLiquidityMinted();
    error InsufficientWithdrawalAmount(uint256 minimum, uint256 received);
    error ActivePositionRequired();

    event LiquidityDeposited(
        uint256 amount0G,
        uint256 strategyShares,
        uint128 liquidityAdded,
        uint256 tokenId
    );

    event LiquidityWithdrawn(
        uint256 strategyShares,
        uint128 liquidityRemoved,
        uint256 amount0G
    );

    modifier onlyVault() {
        if (msg.sender != vault) revert OnlyVault(msg.sender);
        _;
    }

    constructor(
        address vault_,
        address factory_,
        address router_,
        address positionManager_,
        address pool_,
        address w0g_,
        address usdce_,
        uint24 feeTier_,
        int24 tickLower_,
        int24 tickUpper_,
        uint160 sqrtLowerX96_,
        uint160 sqrtUpperX96_,
        RouterMode routerMode_
    ) {
        if (vault_ == address(0)) revert ZeroVault();

        _requireContract(factory_);
        _requireContract(router_);
        _requireContract(positionManager_);
        _requireContract(pool_);
        _requireContract(w0g_);
        _requireContract(usdce_);

        if (tickLower_ >= tickUpper_) {
            revert InvalidTicks(tickLower_, tickUpper_);
        }
        if (
            sqrtLowerX96_ == 0
            || sqrtLowerX96_ >= sqrtUpperX96_
        ) {
            revert InvalidSqrtBounds(
                sqrtLowerX96_,
                sqrtUpperX96_
            );
        }

        address expectedPool = IV3Factory(factory_).getPool(
            w0g_,
            usdce_,
            feeTier_
        );
        if (expectedPool != pool_) {
            revert InvalidPool(
                expectedPool,
                pool_
            );
        }

        IV3Pool poolContract = IV3Pool(pool_);

        address token0_ = poolContract.token0();
        address token1_ = poolContract.token1();

        bool correctPair =
            (token0_ == w0g_ && token1_ == usdce_)
            || (token0_ == usdce_ && token1_ == w0g_);

        if (
            !correctPair
            || poolContract.fee() != feeTier_
            || poolContract.factory() != factory_
        ) {
            revert PoolMetadataMismatch();
        }

        if (
            IV3PeripheryMetadata(router_).factory()
                != factory_
        ) {
            revert PeripheryFactoryMismatch(
                factory_,
                IV3PeripheryMetadata(router_).factory()
            );
        }

        if (
            IV3PeripheryMetadata(positionManager_).factory()
                != factory_
        ) {
            revert PeripheryFactoryMismatch(
                factory_,
                IV3PeripheryMetadata(positionManager_).factory()
            );
        }

        vault = vault_;
        factory = IV3Factory(factory_);
        router = router_;
        positionManager =
            IV3PositionManager(positionManager_);
        pool = poolContract;
        w0g = IW0G(w0g_);
        usdce = IERC20(usdce_);
        feeTier = feeTier_;
        tickLower = tickLower_;
        tickUpper = tickUpper_;
        sqrtLowerX96 = sqrtLowerX96_;
        sqrtUpperX96 = sqrtUpperX96_;
        routerMode = routerMode_;
    }

    receive() external payable {}

    function inputAsset()
        external
        pure
        override
        returns (address)
    {
        return address(0);
    }

    function isAsyncWithdrawal()
        external
        pure
        override
        returns (bool)
    {
        return false;
    }

    function deposit(
        uint256 amount,
        uint256 minShares,
        bytes calldata data
    )
        external
        payable
        override
        onlyVault
        nonReentrant
        returns (uint256 sharesReceived)
    {
        if (amount == 0) revert ZeroAmount();
        if (minShares == 0) revert ZeroMinShares();
        if (msg.value != amount) {
            revert InvalidNativeValue(
                amount,
                msg.value
            );
        }

        (
            uint256 minSwapOutUSDC,
            uint256 amount0Min,
            uint256 amount1Min,
            uint256 deadline
        ) = _decodeExecutionData(data);

        _checkDeadline(deadline);

        uint256 swapAmount = amount / 2;
        uint256 keepAmount = amount - swapAmount;

        w0g.deposit{value: amount}();

        uint256 usdcReceived = 0;
        if (swapAmount != 0) {
            usdcReceived = _swap(
                address(w0g),
                address(usdce),
                swapAmount,
                minSwapOutUSDC,
                deadline
            );
        }

        uint256 liquidityBefore =
            _positionLiquidity();

        (
            uint128 liquidityAdded,
            uint256 positionTokenId
        ) = _addLiquidity(
            keepAmount,
            usdcReceived,
            amount0Min,
            amount1Min,
            deadline
        );

        if (liquidityAdded == 0) {
            revert ZeroLiquidityMinted();
        }

        if (tokenId == 0) {
            tokenId = positionTokenId;
            sharesReceived =
                uint256(liquidityAdded);
        } else {
            if (positionTokenId != tokenId) {
                revert InvalidPositionTokenId(
                    tokenId,
                    positionTokenId
                );
            }

            if (
                totalStrategyShares == 0
                || liquidityBefore == 0
            ) {
                revert ActivePositionRequired();
            }

            sharesReceived = Math.mulDiv(
                uint256(liquidityAdded),
                totalStrategyShares,
                liquidityBefore
            );
        }

        if (sharesReceived < minShares) {
            revert InsufficientShares(
                minShares,
                sharesReceived
            );
        }

        totalStrategyShares += sharesReceived;


        emit LiquidityDeposited(
            amount,
            sharesReceived,
            liquidityAdded,
            tokenId
        );
    }

    function requestWithdraw(
        uint256 shares,
        uint256 minAmountOut,
        bytes calldata data
    )
        external
        override
        onlyVault
        nonReentrant
        returns (
            bytes32 requestId,
            uint256 amountOut,
            bool pending
        )
    {
        if (shares == 0) revert ZeroAmount();
        if (minAmountOut == 0) revert ZeroMinAmountOut();

        uint256 totalShares = totalStrategyShares;
        if (
            totalShares == 0
            || tokenId == 0
        ) {
            revert ActivePositionRequired();
        }
        if (shares > totalShares) {
            revert InsufficientStrategyShares(
                totalShares,
                shares
            );
        }

        (
            uint256 minSwapOutW0G,
            uint256 amount0Min,
            uint256 amount1Min,
            uint256 deadline
        ) = _decodeExecutionData(data);

        _checkDeadline(deadline);

        uint128 liquidity =
            _positionLiquidity();

        uint128 removeLiquidity = uint128(
            Math.mulDiv(
                uint256(liquidity),
                shares,
                totalShares
            )
        );

        if (removeLiquidity == 0) {
            revert ZeroLiquidityMinted();
        }

        (
            uint256 amount0,
            uint256 amount1
        ) = _removeLiquidity(
            removeLiquidity,
            amount0Min,
            amount1Min,
            deadline
        );

        totalStrategyShares =
            totalShares - shares;

        uint256 w0gAmount;
        uint256 usdcAmount;

        if (
            pool.token0()
                == address(w0g)
        ) {
            w0gAmount = amount0;
            usdcAmount = amount1;
        } else {
            w0gAmount = amount1;
            usdcAmount = amount0;
        }

        if (usdcAmount != 0) {
            w0gAmount += _swap(
                address(usdce),
                address(w0g),
                usdcAmount,
                minSwapOutW0G,
                deadline
            );
        }

        uint256 nativeBefore =
            address(this).balance;

        if (w0gAmount != 0) {
            w0g.withdraw(w0gAmount);
        }

        amountOut =
            address(this).balance
            - nativeBefore;

        if (amountOut < minAmountOut) {
            revert InsufficientWithdrawalAmount(
                minAmountOut,
                amountOut
            );
        }

        payable(vault).sendValue(amountOut);

        if (totalStrategyShares == 0) {
            _closeEmptyPosition();
        }


        emit LiquidityWithdrawn(
            shares,
            removeLiquidity,
            amountOut
        );

        return (
            bytes32(0),
            amountOut,
            false
        );
    }

    function claimWithdraw(
        bytes32,
        uint256,
        bytes calldata
    )
        external
        pure
        override
        returns (uint256)
    {
        revert("V3_SYNC_ONLY");
    }

    function totalAssets()
        external
        view
        override
        returns (uint256)
    {
        uint256 shares =
            totalStrategyShares;

        if (
            shares == 0
            || tokenId == 0
        ) {
            return 0;
        }

        return _previewRedeem(shares);
    }

    function previewRedeem(uint256 shares)
        external
        view
        override
        returns (uint256 amountOut)
    {
        if (shares == 0) return 0;

        if (shares > totalStrategyShares) {
            return 0;
        }

        return _previewRedeem(shares);
    }

    function _previewRedeem(uint256 shares)
        private
        view
        returns (uint256 amountOut)
    {
        uint256 totalShares =
            totalStrategyShares;

        if (
            totalShares == 0
            || tokenId == 0
        ) {
            return 0;
        }

        uint128 liquidity =
            _positionLiquidity();

        uint128 shareLiquidity = uint128(
            Math.mulDiv(
                uint256(liquidity),
                shares,
                totalShares
            )
        );

        (
            uint160 sqrtPriceX96,,,,,,
        ) = pool.slot0();

        (
            uint256 amount0,
            uint256 amount1
        ) = V3PositionMath.amountsForLiquidity(
            sqrtPriceX96,
            sqrtLowerX96,
            sqrtUpperX96,
            shareLiquidity
        );

        // Any unspent mint/increase-liquidity dust stays inside the pooled
        // strategy. Value it pro rata instead of sending it to AscendVault
        // without a corresponding user idle-balance credit.
        uint256 dustW0G = Math.mulDiv(
            w0g.balanceOf(address(this)),
            shares,
            totalShares
        );
        uint256 dustUSDC = Math.mulDiv(
            usdce.balanceOf(address(this)),
            shares,
            totalShares
        );

        if (
            pool.token0()
                == address(w0g)
        ) {
            return V3PositionMath.valueInToken0(
                amount0 + dustW0G,
                amount1 + dustUSDC,
                sqrtPriceX96
            );
        }

        // token1 is W0G. Convert token0 (USDC.e) into token1 units.
        return V3PositionMath.valueInToken1(
            amount0 + dustUSDC,
            amount1 + dustW0G,
            sqrtPriceX96
        );
    }

    function _addLiquidity(
        uint256 w0gDesired,
        uint256 usdcDesired,
        uint256 amount0Min,
        uint256 amount1Min,
        uint256 deadline
    )
        private
        returns (
            uint128 liquidityAdded,
            uint256 positionTokenId
        )
    {
        address token0_ = pool.token0();

        uint256 amount0Desired =
            token0_ == address(w0g)
                ? w0gDesired
                : usdcDesired;

        uint256 amount1Desired =
            token0_ == address(w0g)
                ? usdcDesired
                : w0gDesired;

        w0g.forceApprove(
            address(positionManager),
            w0gDesired
        );
        usdce.forceApprove(
            address(positionManager),
            usdcDesired
        );

        if (tokenId == 0) {
            (
                positionTokenId,
                liquidityAdded,,
            ) = positionManager.mint(
                IV3PositionManager.MintParams({
                    token0: pool.token0(),
                    token1: pool.token1(),
                    fee: feeTier,
                    tickLower: tickLower,
                    tickUpper: tickUpper,
                    amount0Desired: amount0Desired,
                    amount1Desired: amount1Desired,
                    amount0Min: amount0Min,
                    amount1Min: amount1Min,
                    recipient: address(this),
                    deadline: deadline
                })
            );
        } else {
            (
                liquidityAdded,,
            ) = positionManager.increaseLiquidity(
                IV3PositionManager.IncreaseLiquidityParams({
                    tokenId: tokenId,
                    amount0Desired: amount0Desired,
                    amount1Desired: amount1Desired,
                    amount0Min: amount0Min,
                    amount1Min: amount1Min,
                    deadline: deadline
                })
            );

            positionTokenId = tokenId;
        }

        w0g.forceApprove(
            address(positionManager),
            0
        );
        usdce.forceApprove(
            address(positionManager),
            0
        );
    }

    function _removeLiquidity(
        uint128 liquidity,
        uint256 amount0Min,
        uint256 amount1Min,
        uint256 deadline
    )
        private
        returns (
            uint256 amount0,
            uint256 amount1
        )
    {
        (
            uint256 principal0,
            uint256 principal1
        ) = positionManager.decreaseLiquidity(
            IV3PositionManager.DecreaseLiquidityParams({
                tokenId: tokenId,
                liquidity: liquidity,
                amount0Min: amount0Min,
                amount1Min: amount1Min,
                deadline: deadline
            })
        );

        // Collect only the principal just released by decreaseLiquidity.
        // Pre-existing trading fees remain attached to the pooled NFT and are
        // not accidentally handed to the user who happens to withdraw first.
        (
            amount0,
            amount1
        ) = positionManager.collect(
            IV3PositionManager.CollectParams({
                tokenId: tokenId,
                recipient: address(this),
                amount0Max: _toUint128(principal0),
                amount1Max: _toUint128(principal1)
            })
        );
    }

    function _closeEmptyPosition()
        private
    {
        uint256 currentTokenId = tokenId;

        (
            ,,,,,,,
            uint128 liquidity,,,
            uint128 owed0,
            uint128 owed1
        ) = positionManager.positions(
            currentTokenId
        );

        if (
            liquidity == 0
            && owed0 == 0
            && owed1 == 0
        ) {
            positionManager.burn(
                currentTokenId
            );
            tokenId = 0;
        }
    }

    function _swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    )
        private
        returns (uint256 amountOut)
    {
        IERC20(tokenIn).forceApprove(
            router,
            amountIn
        );

        if (routerMode == RouterMode.V1) {
            amountOut =
                IV3SwapRouterV1(router)
                    .exactInputSingle(
                        IV3SwapRouterV1.ExactInputSingleParams({
                            tokenIn: tokenIn,
                            tokenOut: tokenOut,
                            fee: feeTier,
                            recipient: address(this),
                            deadline: deadline,
                            amountIn: amountIn,
                            amountOutMinimum: minAmountOut,
                            sqrtPriceLimitX96: 0
                        })
                    );
        } else {
            amountOut =
                IV3SwapRouter02(router)
                    .exactInputSingle(
                        IV3SwapRouter02.ExactInputSingleParams({
                            tokenIn: tokenIn,
                            tokenOut: tokenOut,
                            fee: feeTier,
                            recipient: address(this),
                            amountIn: amountIn,
                            amountOutMinimum: minAmountOut,
                            sqrtPriceLimitX96: 0
                        })
                    );
        }

        IERC20(tokenIn).forceApprove(
            router,
            0
        );
    }

    function _positionLiquidity()
        private
        view
        returns (uint128 liquidity)
    {
        if (tokenId == 0) {
            return 0;
        }

        (
            ,,,,,,,
            liquidity,,,,
        ) = positionManager.positions(
            tokenId
        );
    }

    function _toUint128(uint256 value)
        private
        pure
        returns (uint128)
    {
        if (value > type(uint128).max) {
            return type(uint128).max;
        }
        return uint128(value);
    }

    function _decodeExecutionData(
        bytes calldata data
    )
        private
        pure
        returns (
            uint256 swapMinimum,
            uint256 amount0Min,
            uint256 amount1Min,
            uint256 deadline
        )
    {
        if (data.length != 128) {
            revert InvalidExecutionData();
        }

        return abi.decode(
            data,
            (
                uint256,
                uint256,
                uint256,
                uint256
            )
        );
    }

    function _checkDeadline(uint256 deadline)
        private
        view
    {
        if (block.timestamp > deadline) {
            revert AllocationExpired(
                deadline,
                block.timestamp
            );
        }
    }

    function _requireContract(address target)
        private
        view
    {
        if (
            target == address(0)
            || target.code.length == 0
        ) {
            revert InvalidContract(target);
        }
    }
}
