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
///      Vault shares are synthetic NAV shares denominated against the pooled
///      position's current W0G-equivalent value. Active liquidity, uncollected
///      V3 fees, and residual W0G/USDC.e dust are all included in NAV.
///
///      Withdrawals take only their pro-rata slice of active liquidity, accrued
///      fees, and dust. This prevents a late depositor from capturing old fees
///      and prevents an early withdrawer from sweeping fees owed to other users.
///      LP fees are therefore embedded in strategy-share value and are NOT
///      duplicated through RewardAccounting.
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

    struct ExecutionData {
        uint256 swapMinimum;
        uint256 amount0Min;
        uint256 amount1Min;
        uint256 deadline;
    }

    struct WithdrawalAmounts {
        uint128 liquidityRemoved;
        uint256 w0gAmount;
        uint256 usdcAmount;
    }

    struct PrincipalAmounts {
        uint256 amount0;
        uint256 amount1;
    }

    struct OwedAmounts {
        uint256 amount0;
        uint256 amount1;
    }

    struct DeploymentConfig {
        address vault;
        address factory;
        address router;
        address positionManager;
        address pool;
        address w0g;
        address usdce;
        uint24 feeTier;
        int24 tickLower;
        int24 tickUpper;
        uint160 sqrtLowerX96;
        uint160 sqrtUpperX96;
        RouterMode routerMode;
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
    error ZeroContributionValue();
    error InvalidPoolAccounting();
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
        DeploymentConfig memory config
    ) {
        _validateDeployment(config);

        vault = config.vault;
        factory = IV3Factory(config.factory);
        router = config.router;
        positionManager =
            IV3PositionManager(config.positionManager);
        pool = IV3Pool(config.pool);
        w0g = IW0G(config.w0g);
        usdce = IERC20(config.usdce);
        feeTier = config.feeTier;
        tickLower = config.tickLower;
        tickUpper = config.tickUpper;
        sqrtLowerX96 = config.sqrtLowerX96;
        sqrtUpperX96 = config.sqrtUpperX96;
        routerMode = config.routerMode;
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

        ExecutionData memory execution =
            _decodeExecutionData(data);

        _checkDeadline(execution.deadline);

        uint256 sharesBefore =
            totalStrategyShares;
        uint256 navBefore =
            _grossAssetsValue();

        uint256 swapAmount = amount / 2;
        uint256 keepAmount = amount - swapAmount;

        w0g.deposit{value: amount}();

        uint256 usdcReceived;
        if (swapAmount != 0) {
            usdcReceived = _swap(
                address(w0g),
                address(usdce),
                swapAmount,
                execution.swapMinimum,
                execution.deadline
            );
        }

        (
            uint128 liquidityAdded,
            uint256 positionTokenId
        ) = _addLiquidity(
            keepAmount,
            usdcReceived,
            execution.amount0Min,
            execution.amount1Min,
            execution.deadline
        );

        if (liquidityAdded == 0) {
            revert ZeroLiquidityMinted();
        }

        if (tokenId == 0) {
            tokenId = positionTokenId;
        } else if (positionTokenId != tokenId) {
            revert InvalidPositionTokenId(
                tokenId,
                positionTokenId
            );
        }

        uint256 navAfter =
            _grossAssetsValue();

        if (navAfter <= navBefore) {
            revert ZeroContributionValue();
        }

        uint256 contributionValue =
            navAfter - navBefore;

        if (sharesBefore == 0) {
            sharesReceived =
                contributionValue;
        } else {
            if (navBefore == 0) {
                revert InvalidPoolAccounting();
            }

            sharesReceived = Math.mulDiv(
                contributionValue,
                sharesBefore,
                navBefore
            );
        }

        if (sharesReceived < minShares) {
            revert InsufficientShares(
                minShares,
                sharesReceived
            );
        }

        totalStrategyShares =
            sharesBefore + sharesReceived;

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
        uint256 totalShares =
            _validateWithdrawal(
                shares,
                minAmountOut
            );

        ExecutionData memory execution =
            _decodeExecutionData(data);

        _checkDeadline(execution.deadline);

        WithdrawalAmounts memory amounts =
            _withdrawPositionShare(
                shares,
                totalShares,
                execution
            );

        totalStrategyShares =
            totalShares - shares;

        amountOut = _settleWithdrawal(
            amounts.w0gAmount,
            amounts.usdcAmount,
            execution.swapMinimum,
            execution.deadline
        );

        if (amountOut < minAmountOut) {
            revert InsufficientWithdrawalAmount(
                minAmountOut,
                amountOut
            );
        }

        payable(vault).sendValue(
            amountOut
        );

        if (totalStrategyShares == 0) {
            _closeEmptyPosition();
        }

        emit LiquidityWithdrawn(
            shares,
            amounts.liquidityRemoved,
            amountOut
        );

        return (
            bytes32(0),
            amountOut,
            false
        );
    }

    function _validateWithdrawal(
        uint256 shares,
        uint256 minAmountOut
    )
        private
        view
        returns (uint256 totalShares)
    {
        if (shares == 0) revert ZeroAmount();
        if (minAmountOut == 0) revert ZeroMinAmountOut();

        totalShares =
            totalStrategyShares;

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
    }

    function _withdrawPositionShare(
        uint256 shares,
        uint256 totalShares,
        ExecutionData memory execution
    )
        private
        returns (
            WithdrawalAmounts memory amounts
        )
    {
        uint256 dustW0GShare =
            Math.mulDiv(
                w0g.balanceOf(address(this)),
                shares,
                totalShares
            );

        uint256 dustUSDCShare =
            Math.mulDiv(
                usdce.balanceOf(address(this)),
                shares,
                totalShares
            );

        uint128 liquidity =
            _positionLiquidity();

        amounts.liquidityRemoved =
            uint128(
                Math.mulDiv(
                    uint256(liquidity),
                    shares,
                    totalShares
                )
            );

        if (amounts.liquidityRemoved == 0) {
            revert ZeroLiquidityMinted();
        }

        (
            uint256 amount0,
            uint256 amount1
        ) = _removeLiquidityProRata(
            amounts.liquidityRemoved,
            shares,
            totalShares,
            execution.amount0Min,
            execution.amount1Min,
            execution.deadline
        );

        if (
            pool.token0()
                == address(w0g)
        ) {
            amounts.w0gAmount =
                amount0 + dustW0GShare;
            amounts.usdcAmount =
                amount1 + dustUSDCShare;
        } else {
            amounts.w0gAmount =
                amount1 + dustW0GShare;
            amounts.usdcAmount =
                amount0 + dustUSDCShare;
        }
    }

    function _settleWithdrawal(
        uint256 w0gAmount,
        uint256 usdcAmount,
        uint256 minSwapOutW0G,
        uint256 deadline
    )
        private
        returns (uint256 amountOut)
    {
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

        return (
            address(this).balance
            - nativeBefore
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
        return _grossAssetsValue();
    }

    function previewRedeem(uint256 shares)
        external
        view
        override
        returns (uint256 amountOut)
    {
        uint256 totalShares =
            totalStrategyShares;

        if (
            shares == 0
            || totalShares == 0
            || shares > totalShares
        ) {
            return 0;
        }

        return Math.mulDiv(
            _grossAssetsValue(),
            shares,
            totalShares
        );
    }

    function _grossAssetsValue()
        private
        view
        returns (uint256)
    {
        (
            uint160 sqrtPriceX96,,,,,,
        ) = pool.slot0();

        uint256 amount0;
        uint256 amount1;

        if (tokenId != 0) {
            (
                ,,,,,,,
                uint128 liquidity,,,
                uint128 owed0,
                uint128 owed1
            ) = positionManager.positions(
                tokenId
            );

            (
                amount0,
                amount1
            ) = V3PositionMath.amountsForLiquidity(
                sqrtPriceX96,
                sqrtLowerX96,
                sqrtUpperX96,
                liquidity
            );

            amount0 += uint256(owed0);
            amount1 += uint256(owed1);
        }

        if (
            pool.token0()
                == address(w0g)
        ) {
            amount0 +=
                w0g.balanceOf(address(this));
            amount1 +=
                usdce.balanceOf(address(this));

            return V3PositionMath.valueInToken0(
                amount0,
                amount1,
                sqrtPriceX96
            );
        }

        amount0 +=
            usdce.balanceOf(address(this));
        amount1 +=
            w0g.balanceOf(address(this));

        return V3PositionMath.valueInToken1(
            amount0,
            amount1,
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

    function _removeLiquidityProRata(
        uint128 liquidity,
        uint256 shares,
        uint256 totalShares,
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
        PrincipalAmounts memory principal =
            _decreaseLiquidity(
                liquidity,
                amount0Min,
                amount1Min,
                deadline
            );

        OwedAmounts memory owed =
            _positionOwed();

        (
            uint128 collect0,
            uint128 collect1
        ) = _proRataCollectMaximums(
            principal,
            owed,
            shares,
            totalShares
        );

        return positionManager.collect(
            IV3PositionManager.CollectParams({
                tokenId: tokenId,
                recipient: address(this),
                amount0Max: collect0,
                amount1Max: collect1
            })
        );
    }

    function _decreaseLiquidity(
        uint128 liquidity,
        uint256 amount0Min,
        uint256 amount1Min,
        uint256 deadline
    )
        private
        returns (PrincipalAmounts memory principal)
    {
        (
            principal.amount0,
            principal.amount1
        ) = positionManager.decreaseLiquidity(
            IV3PositionManager.DecreaseLiquidityParams({
                tokenId: tokenId,
                liquidity: liquidity,
                amount0Min: amount0Min,
                amount1Min: amount1Min,
                deadline: deadline
            })
        );
    }

    function _positionOwed()
        private
        view
        returns (OwedAmounts memory owed)
    {
        (
            ,,,,,,,,,,
            uint128 owed0,
            uint128 owed1
        ) = positionManager.positions(
            tokenId
        );

        owed.amount0 = uint256(owed0);
        owed.amount1 = uint256(owed1);
    }

    function _proRataCollectMaximums(
        PrincipalAmounts memory principal,
        OwedAmounts memory owed,
        uint256 shares,
        uint256 totalShares
    )
        private
        pure
        returns (
            uint128 collect0,
            uint128 collect1
        )
    {
        if (
            owed.amount0 < principal.amount0
            || owed.amount1 < principal.amount1
        ) {
            revert InvalidPoolAccounting();
        }

        uint256 feePool0 =
            owed.amount0 - principal.amount0;
        uint256 feePool1 =
            owed.amount1 - principal.amount1;

        uint256 max0 =
            principal.amount0
            + Math.mulDiv(
                feePool0,
                shares,
                totalShares
            );

        uint256 max1 =
            principal.amount1
            + Math.mulDiv(
                feePool1,
                shares,
                totalShares
            );

        collect0 = _toUint128(max0);
        collect1 = _toUint128(max1);
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
        returns (ExecutionData memory execution)
    {
        if (data.length != 128) {
            revert InvalidExecutionData();
        }

        (
            execution.swapMinimum,
            execution.amount0Min,
            execution.amount1Min,
            execution.deadline
        ) = abi.decode(
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

    function _validateDeployment(
        DeploymentConfig memory config
    )
        private
        view
    {
        if (config.vault == address(0)) {
            revert ZeroVault();
        }

        _requireContract(config.factory);
        _requireContract(config.router);
        _requireContract(config.positionManager);
        _requireContract(config.pool);
        _requireContract(config.w0g);
        _requireContract(config.usdce);

        _validateRange(config);
        _validatePool(config);
        _validatePeriphery(config);
    }

    function _validateRange(
        DeploymentConfig memory config
    )
        private
        pure
    {
        if (config.tickLower >= config.tickUpper) {
            revert InvalidTicks(
                config.tickLower,
                config.tickUpper
            );
        }

        if (
            config.sqrtLowerX96 == 0
            || config.sqrtLowerX96 >= config.sqrtUpperX96
        ) {
            revert InvalidSqrtBounds(
                config.sqrtLowerX96,
                config.sqrtUpperX96
            );
        }
    }

    function _validatePool(
        DeploymentConfig memory config
    )
        private
        view
    {
        address expectedPool =
            IV3Factory(config.factory).getPool(
                config.w0g,
                config.usdce,
                config.feeTier
            );

        if (expectedPool != config.pool) {
            revert InvalidPool(
                expectedPool,
                config.pool
            );
        }

        IV3Pool poolContract =
            IV3Pool(config.pool);

        address token0_ =
            poolContract.token0();
        address token1_ =
            poolContract.token1();

        bool correctPair =
            (
                token0_ == config.w0g
                && token1_ == config.usdce
            )
            || (
                token0_ == config.usdce
                && token1_ == config.w0g
            );

        if (
            !correctPair
            || poolContract.fee() != config.feeTier
            || poolContract.factory() != config.factory
        ) {
            revert PoolMetadataMismatch();
        }
    }

    function _validatePeriphery(
        DeploymentConfig memory config
    )
        private
        view
    {
        address routerFactory =
            IV3PeripheryMetadata(config.router)
                .factory();

        if (routerFactory != config.factory) {
            revert PeripheryFactoryMismatch(
                config.factory,
                routerFactory
            );
        }

        address managerFactory =
            IV3PeripheryMetadata(
                config.positionManager
            ).factory();

        if (managerFactory != config.factory) {
            revert PeripheryFactoryMismatch(
                config.factory,
                managerFactory
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
