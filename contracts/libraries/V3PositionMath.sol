// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

/// @title V3PositionMath
/// @notice Minimal concentrated-liquidity amount/value math for a fixed range.
/// @dev sqrt bounds are supplied by trusted deployment configuration. This
///      avoids importing the full Uniswap V3 math stack into the capstone MVP.
library V3PositionMath {
    uint256 internal constant Q96 = 2 ** 96;

    error InvalidSqrtRange();

    function amountsForLiquidity(
        uint160 sqrtPriceX96,
        uint160 sqrtLowerX96,
        uint160 sqrtUpperX96,
        uint128 liquidity
    )
        internal
        pure
        returns (
            uint256 amount0,
            uint256 amount1
        )
    {
        if (
            sqrtLowerX96 == 0
            || sqrtLowerX96 >= sqrtUpperX96
        ) {
            revert InvalidSqrtRange();
        }

        if (liquidity == 0) {
            return (0, 0);
        }

        if (sqrtPriceX96 <= sqrtLowerX96) {
            amount0 = _amount0(
                sqrtLowerX96,
                sqrtUpperX96,
                liquidity
            );
        } else if (sqrtPriceX96 < sqrtUpperX96) {
            amount0 = _amount0(
                sqrtPriceX96,
                sqrtUpperX96,
                liquidity
            );
            amount1 = _amount1(
                sqrtLowerX96,
                sqrtPriceX96,
                liquidity
            );
        } else {
            amount1 = _amount1(
                sqrtLowerX96,
                sqrtUpperX96,
                liquidity
            );
        }
    }

    function valueInToken0(
        uint256 amount0,
        uint256 amount1,
        uint160 sqrtPriceX96
    ) internal pure returns (uint256) {
        if (sqrtPriceX96 == 0) {
            revert InvalidSqrtRange();
        }

        uint256 token1InToken0 = Math.mulDiv(
            amount1,
            Q96,
            uint256(sqrtPriceX96)
        );
        token1InToken0 = Math.mulDiv(
            token1InToken0,
            Q96,
            uint256(sqrtPriceX96)
        );

        return amount0 + token1InToken0;
    }

    function valueInToken1(
        uint256 amount0,
        uint256 amount1,
        uint160 sqrtPriceX96
    ) internal pure returns (uint256) {
        if (sqrtPriceX96 == 0) {
            revert InvalidSqrtRange();
        }

        uint256 token0InToken1 = Math.mulDiv(
            amount0,
            uint256(sqrtPriceX96),
            Q96
        );
        token0InToken1 = Math.mulDiv(
            token0InToken1,
            uint256(sqrtPriceX96),
            Q96
        );

        return amount1 + token0InToken1;
    }

    function _amount0(
        uint160 sqrtA,
        uint160 sqrtB,
        uint128 liquidity
    ) private pure returns (uint256) {
        uint256 numerator =
            uint256(liquidity) << 96;

        return Math.mulDiv(
            numerator,
            uint256(sqrtB) - uint256(sqrtA),
            uint256(sqrtB)
        ) / uint256(sqrtA);
    }

    function _amount1(
        uint160 sqrtA,
        uint160 sqrtB,
        uint128 liquidity
    ) private pure returns (uint256) {
        return Math.mulDiv(
            uint256(liquidity),
            uint256(sqrtB) - uint256(sqrtA),
            Q96
        );
    }
}
