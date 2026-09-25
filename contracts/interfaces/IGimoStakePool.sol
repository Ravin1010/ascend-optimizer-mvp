// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// @title IGimoStakePool
/// @notice Minimal Gimo/StaFi liquid-staking surface used by GimoAdapter.
/// @dev Gimo's live staking route uses native 0G, mints st0G on stake,
///      burns st0G on unstake, and exposes a parameterless matured withdrawal.
interface IGimoStakePool {
    function stake(string calldata referral) external payable;

    function unstake(uint256 st0gAmount) external;

    function withdraw() external;
}

/// @title IGimoSt0G
/// @notice st0G token surface required for share accounting and valuation.
interface IGimoSt0G is IERC20 {
    /// @notice Native 0G represented by one st0G, scaled by 1e18.
    function getRate() external view returns (uint256);
}
