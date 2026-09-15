// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title I0GValidator
/// @notice Minimal 0G validator interface used by Native0GStakingAdapter.
/// @dev Function signatures are taken from the official 0G staking docs.
interface I0GValidator {
    function delegate(address delegatorAddress)
        external
        payable
        returns (uint256);

    function undelegate(
        address withdrawalAddress,
        uint256 shares
    )
        external
        payable
        returns (uint256);

    function getDelegation(address delegator)
        external
        view
        returns (address validatorAddress, uint256 shares);

    function convertToTokens(uint256 shares)
        external
        view
        returns (uint256);

    function withdrawalFeeInGwei()
        external
        view
        returns (uint96);

    function processWithdrawQueue() external;
}
