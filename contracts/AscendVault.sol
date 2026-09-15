// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Address} from "@openzeppelin/contracts/utils/Address.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {IStrategyAdapter} from "./interfaces/IStrategyAdapter.sol";
import {StrategyManager} from "./StrategyManager.sol";

/// @title AscendVault
/// @notice User-facing custody and user-authorized initial allocation contract.
/// @dev The optimizer has no role in this contract. Recommendations are executed
///      only when the user calls executeAllocation() for their own idle balance.
contract AscendVault is Ownable2Step, Pausable, ReentrancyGuard {
    using Address for address payable;
    using SafeERC20 for IERC20;

    uint16 public constant BPS_DENOMINATOR = 10_000;
    address public constant NATIVE_0G = address(0);

    StrategyManager public immutable strategyManager;

    mapping(address user => mapping(address asset => uint256))
        public idleBalanceOf;

    mapping(address user => mapping(bytes32 strategyId => uint256))
        public strategySharesOf;

    error ZeroStrategyManager();
    error UnsupportedAsset(address asset);
    error ZeroAmount();
    error ZeroRecipient();
    error ZeroMinShares();
    error InsufficientIdleBalance(
        address user,
        address asset,
        uint256 available,
        uint256 requested
    );
    error StrategyInactive(bytes32 strategyId);
    error AllocationExpired(uint256 deadline, uint256 currentTimestamp);
    error StrategyDepositCapExceeded(
        bytes32 strategyId,
        uint256 cap,
        uint256 currentAssets,
        uint256 requested
    );
    error StrategyAllocationCapExceeded(
        bytes32 strategyId,
        uint16 maxAllocationBps,
        uint256 maxAllowedValue,
        uint256 requestedPostAllocationValue
    );
    error InsufficientStrategyShares(
        bytes32 strategyId,
        uint256 minimum,
        uint256 received
    );

    event NativeDeposited(
        address indexed user,
        uint256 amount
    );

    event TokenDeposited(
        address indexed user,
        address indexed token,
        uint256 amount
    );

    event IdleWithdrawn(
        address indexed user,
        address indexed asset,
        address indexed recipient,
        uint256 amount
    );

    event AllocationExecuted(
        address indexed user,
        bytes32 indexed strategyId,
        address indexed inputAsset,
        uint256 amount,
        uint256 sharesReceived
    );

    constructor(
        address initialOwner,
        address strategyManager_
    ) Ownable(initialOwner) {
        if (strategyManager_ == address(0)) {
            revert ZeroStrategyManager();
        }

        strategyManager = StrategyManager(strategyManager_);
    }

    /// @notice Deposit native 0G into the caller's idle balance.
    function depositNative()
        external
        payable
        whenNotPaused
        nonReentrant
    {
        if (msg.value == 0) revert ZeroAmount();
        if (!_isSupportedAsset(NATIVE_0G)) {
            revert UnsupportedAsset(NATIVE_0G);
        }

        idleBalanceOf[msg.sender][NATIVE_0G] += msg.value;

        emit NativeDeposited(msg.sender, msg.value);
    }

    /// @notice Deposit an approved ERC-20 into the caller's idle balance.
    function depositToken(
        address token,
        uint256 amount
    )
        external
        whenNotPaused
        nonReentrant
    {
        if (token == address(0)) {
            revert UnsupportedAsset(token);
        }
        if (amount == 0) revert ZeroAmount();
        if (!_isSupportedAsset(token)) {
            revert UnsupportedAsset(token);
        }

        IERC20(token).safeTransferFrom(
            msg.sender,
            address(this),
            amount
        );

        idleBalanceOf[msg.sender][token] += amount;

        emit TokenDeposited(
            msg.sender,
            token,
            amount
        );
    }

    /// @notice Withdraw capital that has not been allocated to a strategy.
    /// @dev This remains available while deposits/new allocations are paused.
    function withdrawIdle(
        address asset,
        uint256 amount,
        address payable recipient
    ) external nonReentrant {
        if (amount == 0) revert ZeroAmount();
        if (recipient == address(0)) revert ZeroRecipient();

        uint256 available = idleBalanceOf[msg.sender][asset];
        if (available < amount) {
            revert InsufficientIdleBalance(
                msg.sender,
                asset,
                available,
                amount
            );
        }

        idleBalanceOf[msg.sender][asset] = available - amount;

        if (asset == NATIVE_0G) {
            recipient.sendValue(amount);
        } else {
            IERC20(asset).safeTransfer(recipient, amount);
        }

        emit IdleWithdrawn(
            msg.sender,
            asset,
            recipient,
            amount
        );
    }

    /// @notice Execute one optimizer recommendation explicitly authorized by user.
    /// @param strategyId Approved strategy identifier.
    /// @param amount Amount of the strategy's input asset to deploy.
    /// @param minShares Minimum acceptable strategy shares.
    /// @param deadline Latest timestamp at which this instruction is valid.
    /// @param data Bounded protocol-specific adapter parameters.
    function executeAllocation(
        bytes32 strategyId,
        uint256 amount,
        uint256 minShares,
        uint256 deadline,
        bytes calldata data
    )
        external
        whenNotPaused
        nonReentrant
        returns (uint256 sharesReceived)
    {
        if (amount == 0) revert ZeroAmount();
        if (minShares == 0) revert ZeroMinShares();
        if (block.timestamp > deadline) {
            revert AllocationExpired(
                deadline,
                block.timestamp
            );
        }

        StrategyManager.StrategyConfig memory config =
            strategyManager.getStrategy(strategyId);

        if (!config.active) {
            revert StrategyInactive(strategyId);
        }

        address asset = config.inputAsset;
        uint256 available = idleBalanceOf[msg.sender][asset];

        if (available < amount) {
            revert InsufficientIdleBalance(
                msg.sender,
                asset,
                available,
                amount
            );
        }

        _enforceDepositCap(
            strategyId,
            config,
            amount
        );
        _enforceAllocationCap(
            msg.sender,
            strategyId,
            config,
            amount
        );

        // Effects before the external adapter call.
        idleBalanceOf[msg.sender][asset] = available - amount;

        IStrategyAdapter adapter =
            IStrategyAdapter(config.adapter);

        if (asset == NATIVE_0G) {
            sharesReceived = adapter.deposit{value: amount}(
                amount,
                minShares,
                data
            );
        } else {
            IERC20 token = IERC20(asset);
            token.forceApprove(config.adapter, amount);

            sharesReceived = adapter.deposit(
                amount,
                minShares,
                data
            );

            token.forceApprove(config.adapter, 0);
        }

        if (sharesReceived < minShares) {
            revert InsufficientStrategyShares(
                strategyId,
                minShares,
                sharesReceived
            );
        }

        strategySharesOf[msg.sender][strategyId] += sharesReceived;

        emit AllocationExecuted(
            msg.sender,
            strategyId,
            asset,
            amount,
            sharesReceived
        );
    }

    /// @notice Current underlying value of one user's positions for an asset.
    /// @dev Used for on-chain hard allocation ceilings, not APY/risk optimization.
    function userAssetValue(
        address user,
        address asset
    ) public view returns (uint256 totalValue) {
        totalValue = idleBalanceOf[user][asset];

        bytes32[] memory ids = strategyManager.strategyIds();

        for (uint256 i = 0; i < ids.length; ++i) {
            StrategyManager.StrategyConfig memory config =
                strategyManager.getStrategy(ids[i]);

            if (config.inputAsset != asset) continue;

            uint256 shares =
                strategySharesOf[user][ids[i]];

            if (shares == 0) continue;

            totalValue += IStrategyAdapter(
                config.adapter
            ).previewRedeem(shares);
        }
    }

    function pauseDepositsAndAllocations()
        external
        onlyOwner
    {
        _pause();
    }

    function unpauseDepositsAndAllocations()
        external
        onlyOwner
    {
        _unpause();
    }

    function _enforceDepositCap(
        bytes32 strategyId,
        StrategyManager.StrategyConfig memory config,
        uint256 amount
    ) private view {
        uint256 currentAssets =
            IStrategyAdapter(config.adapter).totalAssets();

        if (
            currentAssets > config.depositCap
            || amount > config.depositCap - currentAssets
        ) {
            revert StrategyDepositCapExceeded(
                strategyId,
                config.depositCap,
                currentAssets,
                amount
            );
        }
    }

    function _enforceAllocationCap(
        address user,
        bytes32 strategyId,
        StrategyManager.StrategyConfig memory config,
        uint256 amount
    ) private view {
        uint256 totalValue =
            userAssetValue(user, config.inputAsset);

        uint256 existingValue =
            IStrategyAdapter(config.adapter).previewRedeem(
                strategySharesOf[user][strategyId]
            );

        uint256 maxAllowed = Math.mulDiv(
            totalValue,
            config.maxAllocationBps,
            BPS_DENOMINATOR
        );

        uint256 postAllocationValue =
            existingValue + amount;

        if (postAllocationValue > maxAllowed) {
            revert StrategyAllocationCapExceeded(
                strategyId,
                config.maxAllocationBps,
                maxAllowed,
                postAllocationValue
            );
        }
    }

    function _isSupportedAsset(address asset)
        private
        view
        returns (bool)
    {
        bytes32[] memory ids = strategyManager.strategyIds();

        for (uint256 i = 0; i < ids.length; ++i) {
            StrategyManager.StrategyConfig memory config =
                strategyManager.getStrategy(ids[i]);

            if (config.active && config.inputAsset == asset) {
                return true;
            }
        }

        return false;
    }
}
