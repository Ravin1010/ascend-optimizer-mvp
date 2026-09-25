// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {
    IW0G,
    IV3Factory,
    IV3Pool,
    IV3PositionManager,
    IV3SwapRouterV1,
    IV3SwapRouter02
} from "../interfaces/IV3Liquidity.sol";

contract MockW0G is ERC20 {
    constructor() ERC20("Wrapped 0G", "W0G") {}

    receive() external payable {
        deposit();
    }

    function deposit() public payable {
        _mint(msg.sender, msg.value);
    }

    function withdraw(uint256 amount) external {
        _burn(msg.sender, amount);
        payable(msg.sender).transfer(amount);
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract MockUSDCe is ERC20 {
    constructor() ERC20("Mock USDC.e", "USDC.e") {}

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract MockV3Factory is IV3Factory {
    address public pool;

    function setPool(address pool_) external {
        pool = pool_;
    }

    function getPool(
        address,
        address,
        uint24
    ) external view returns (address) {
        return pool;
    }
}

contract MockV3Pool is IV3Pool {
    address public immutable override factory;
    address public immutable override token0;
    address public immutable override token1;
    uint24 public immutable override fee;
    int24 public immutable override tickSpacing;

    uint160 public sqrtPriceX96 = uint160(1 << 96);
    int24 public tick;

    constructor(
        address factory_,
        address token0_,
        address token1_,
        uint24 fee_
    ) {
        factory = factory_;
        token0 = token0_;
        token1 = token1_;
        fee = fee_;
        tickSpacing = 60;
    }

    function setPrice(uint160 sqrtPriceX96_, int24 tick_) external {
        sqrtPriceX96 = sqrtPriceX96_;
        tick = tick_;
    }

    function slot0()
        external
        view
        returns (
            uint160,
            int24,
            uint16,
            uint16,
            uint16,
            uint8,
            bool
        )
    {
        return (
            sqrtPriceX96,
            tick,
            0,
            0,
            0,
            0,
            true
        );
    }
}

abstract contract MockV3RouterBase {
    using SafeERC20 for IERC20;

    address public immutable factory;

    constructor(address factory_) {
        factory = factory_;
    }

    function _swap(
        address tokenIn,
        address tokenOut,
        address recipient,
        uint256 amountIn,
        uint256 amountOutMinimum
    ) internal returns (uint256 amountOut) {
        amountOut = amountIn;
        require(
            amountOut >= amountOutMinimum,
            "min out"
        );

        IERC20(tokenIn).safeTransferFrom(
            msg.sender,
            address(this),
            amountIn
        );

        IERC20(tokenOut).safeTransfer(
            recipient,
            amountOut
        );
    }
}

contract MockV3RouterV1 is
    MockV3RouterBase,
    IV3SwapRouterV1
{
    constructor(address factory_)
        MockV3RouterBase(factory_)
    {}

    function exactInputSingle(
        ExactInputSingleParams calldata params
    ) external payable returns (uint256 amountOut) {
        require(block.timestamp <= params.deadline, "expired");
        return _swap(
            params.tokenIn,
            params.tokenOut,
            params.recipient,
            params.amountIn,
            params.amountOutMinimum
        );
    }
}

contract MockV3Router02 is
    MockV3RouterBase,
    IV3SwapRouter02
{
    constructor(address factory_)
        MockV3RouterBase(factory_)
    {}

    function exactInputSingle(
        ExactInputSingleParams calldata params
    ) external payable returns (uint256 amountOut) {
        return _swap(
            params.tokenIn,
            params.tokenOut,
            params.recipient,
            params.amountIn,
            params.amountOutMinimum
        );
    }
}

contract MockV3PositionManager is IV3PositionManager {
    using SafeERC20 for IERC20;

    address public immutable override factory;

    uint256 public nextTokenId = 1;

    struct Position {
        address token0;
        address token1;
        uint24 fee;
        int24 tickLower;
        int24 tickUpper;
        uint128 liquidity;
        uint128 owed0;
        uint128 owed1;
    }

    mapping(uint256 => Position) public positionOf;

    constructor(address factory_) {
        factory = factory_;
    }

    function mint(MintParams calldata params)
        external
        payable
        returns (
            uint256 tokenId,
            uint128 liquidity,
            uint256 amount0,
            uint256 amount1
        )
    {
        require(block.timestamp <= params.deadline, "expired");

        amount0 = params.amount0Desired;
        amount1 = params.amount1Desired;
        require(amount0 >= params.amount0Min, "min0");
        require(amount1 >= params.amount1Min, "min1");

        liquidity = uint128(
            amount0 < amount1 ? amount0 : amount1
        );
        require(liquidity > 0, "zero liq");

        IERC20(params.token0).safeTransferFrom(
            msg.sender,
            address(this),
            amount0
        );
        IERC20(params.token1).safeTransferFrom(
            msg.sender,
            address(this),
            amount1
        );

        tokenId = nextTokenId++;

        positionOf[tokenId] = Position({
            token0: params.token0,
            token1: params.token1,
            fee: params.fee,
            tickLower: params.tickLower,
            tickUpper: params.tickUpper,
            liquidity: liquidity,
            owed0: 0,
            owed1: 0
        });
    }

    function increaseLiquidity(
        IncreaseLiquidityParams calldata params
    )
        external
        payable
        returns (
            uint128 liquidity,
            uint256 amount0,
            uint256 amount1
        )
    {
        require(block.timestamp <= params.deadline, "expired");

        Position storage p = positionOf[params.tokenId];

        amount0 = params.amount0Desired;
        amount1 = params.amount1Desired;
        require(amount0 >= params.amount0Min, "min0");
        require(amount1 >= params.amount1Min, "min1");

        liquidity = uint128(
            amount0 < amount1 ? amount0 : amount1
        );
        require(liquidity > 0, "zero liq");

        IERC20(p.token0).safeTransferFrom(
            msg.sender,
            address(this),
            amount0
        );
        IERC20(p.token1).safeTransferFrom(
            msg.sender,
            address(this),
            amount1
        );

        p.liquidity += liquidity;
    }

    function decreaseLiquidity(
        DecreaseLiquidityParams calldata params
    )
        external
        payable
        returns (
            uint256 amount0,
            uint256 amount1
        )
    {
        require(block.timestamp <= params.deadline, "expired");

        Position storage p = positionOf[params.tokenId];
        require(p.liquidity >= params.liquidity, "liquidity");

        p.liquidity -= params.liquidity;

        amount0 = params.liquidity;
        amount1 = params.liquidity;

        require(amount0 >= params.amount0Min, "min0");
        require(amount1 >= params.amount1Min, "min1");

        p.owed0 += uint128(amount0);
        p.owed1 += uint128(amount1);
    }

    function collect(CollectParams calldata params)
        external
        payable
        returns (
            uint256 amount0,
            uint256 amount1
        )
    {
        Position storage p = positionOf[params.tokenId];

        amount0 = p.owed0 < params.amount0Max
            ? p.owed0
            : params.amount0Max;
        amount1 = p.owed1 < params.amount1Max
            ? p.owed1
            : params.amount1Max;

        p.owed0 -= uint128(amount0);
        p.owed1 -= uint128(amount1);

        IERC20(p.token0).safeTransfer(
            params.recipient,
            amount0
        );
        IERC20(p.token1).safeTransfer(
            params.recipient,
            amount1
        );
    }

    function burn(uint256 tokenId) external payable {
        Position storage p = positionOf[tokenId];
        require(p.liquidity == 0, "liquidity");
        require(p.owed0 == 0 && p.owed1 == 0, "owed");
        delete positionOf[tokenId];
    }

    function positions(uint256 tokenId)
        external
        view
        returns (
            uint96 nonce,
            address operator,
            address token0,
            address token1,
            uint24 fee,
            int24 tickLower,
            int24 tickUpper,
            uint128 liquidity,
            uint256 feeGrowthInside0LastX128,
            uint256 feeGrowthInside1LastX128,
            uint128 tokensOwed0,
            uint128 tokensOwed1
        )
    {
        Position storage p = positionOf[tokenId];

        return (
            0,
            address(0),
            p.token0,
            p.token1,
            p.fee,
            p.tickLower,
            p.tickUpper,
            p.liquidity,
            0,
            0,
            p.owed0,
            p.owed1
        );
    }

    function addFees(
        uint256 tokenId,
        uint128 amount0,
        uint128 amount1
    ) external {
        Position storage p = positionOf[tokenId];

        if (amount0 != 0) {
            IERC20(p.token0).safeTransferFrom(
                msg.sender,
                address(this),
                amount0
            );
            p.owed0 += amount0;
        }

        if (amount1 != 0) {
            IERC20(p.token1).safeTransferFrom(
                msg.sender,
                address(this),
                amount1
            );
            p.owed1 += amount1;
        }
    }
}
