// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IRestakingConnector
/// @notice Protocol-specific boundary consumed by the generic RestakingAdapter.
/// @dev This interface is intentionally protocol-agnostic. A concrete connector
///      should wrap a verified restaking protocol API rather than teaching the
///      user-facing vault arbitrary external calls.
interface IRestakingConnector {
    /// @notice Asset supplied to the restaking protocol.
    function inputAsset() external view returns (address);

    /// @notice Whether exits require a request/claim lifecycle.
    function isAsyncWithdrawal() external view returns (bool);

    /// @notice Deploy assets into the fixed restaking protocol integration.
    function deposit(
        uint256 amount,
        uint256 minShares,
        bytes calldata data
    ) external payable returns (uint256 sharesReceived);

    /// @notice Begin an exit from the restaking protocol.
    function requestWithdraw(
        uint256 shares,
        uint256 minAmountOut,
        bytes calldata data
    )
        external
        returns (
            bytes32 requestId,
            uint256 amountOut,
            bool pending
        );

    /// @notice Finalize an asynchronous restaking exit.
    function claimWithdraw(
        bytes32 requestId,
        uint256 minAmountOut,
        bytes calldata data
    ) external returns (uint256 amountOut);

    /// @notice Current underlying value managed by this connector.
    function totalAssets() external view returns (uint256);

    /// @notice Estimate assets represented by connector shares.
    function previewRedeem(uint256 shares)
        external
        view
        returns (uint256 amountOut);
}
