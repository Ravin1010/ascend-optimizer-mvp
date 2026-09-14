// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IStrategyAdapter
/// @notice Common execution boundary between AscendVault and protocol adapters.
/// @dev The optimizer never calls adapters directly. Only user-authorized vault
///      execution should reach an approved adapter through StrategyManager.
interface IStrategyAdapter {
    /// @notice Asset accepted by the adapter. address(0) represents native 0G.
    function inputAsset() external view returns (address);

    /// @notice Whether withdrawals require a delayed request/claim lifecycle.
    function isAsyncWithdrawal() external view returns (bool);

    /// @notice Deposit strategy capital and return strategy shares received.
    /// @param amount Amount of input asset to deploy.
    /// @param minShares Minimum acceptable strategy shares.
    /// @param data Bounded protocol-specific execution parameters.
    function deposit(
        uint256 amount,
        uint256 minShares,
        bytes calldata data
    ) external payable returns (uint256 sharesReceived);

    /// @notice Begin a withdrawal.
    /// @return requestId Adapter request identifier for async withdrawals.
    /// @return amountOut Immediate returned amount for synchronous withdrawals.
    /// @return pending True when claimWithdraw must be called later.
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

    /// @notice Finalize an asynchronous withdrawal.
    function claimWithdraw(
        bytes32 requestId,
        uint256 minAmountOut,
        bytes calldata data
    ) external returns (uint256 amountOut);

    /// @notice Current underlying-asset value managed by this adapter.
    function totalAssets() external view returns (uint256);

    /// @notice Estimate underlying assets represented by strategy shares.
    function previewRedeem(uint256 shares)
        external
        view
        returns (uint256 amountOut);
}
