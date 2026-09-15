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
/// @notice User-facing custody and user-authorized strategy execution contract.
/// @dev The optimizer has no role in this contract. Recommendations are executed
///      only when the user calls executeAllocation() for their own idle balance.
contract AscendVault is Ownable2Step, Pausable, ReentrancyGuard {
    using Address for address payable;
    using SafeERC20 for IERC20;

    uint16 public constant BPS_DENOMINATOR = 10_000;
    address public constant NATIVE_0G = address(0);

    StrategyManager public immutable strategyManager;

    struct PendingWithdrawal {
        address user;
        bytes32 strategyId;
        bytes32 adapterRequestId;
        address asset;
        uint256 shares;
        uint256 minimumAmountOut;
        bool active;
    }

    mapping(address user => mapping(address asset => uint256))
        public idleBalanceOf;

    mapping(address user => mapping(bytes32 strategyId => uint256))
        public strategySharesOf;

    mapping(bytes32 withdrawalKey => PendingWithdrawal)
        public pendingWithdrawalOf;

    mapping(address user => uint256)
        public withdrawalNonceOf;

    error ZeroStrategyManager();
    error UnsupportedAsset(address asset);
    error ZeroAmount();
    error ZeroRecipient();
    error ZeroMinShares();
    error ZeroMinAmountOut();
    error ZeroAdapterRequestId();
    error InsufficientIdleBalance(
        address user,
        address asset,
        uint256 available,
        uint256 requested
    );
    error InsufficientUserStrategyShares(
        address user,
        bytes32 strategyId,
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
    error InsufficientWithdrawalAmount(
        bytes32 strategyId,
        uint256 minimum,
        uint256 received
    );
    error AdapterAmountMismatch(
        bytes32 strategyId,
        uint256 reported,
        uint256 received
    );
    error UnexpectedWithdrawalMode(
        bytes32 strategyId,
        bool configuredAsync,
        bool adapterPending
    );
    error PendingWithdrawalNotFound(bytes32 withdrawalKey);
    error PendingWithdrawalNotOwned(
        bytes32 withdrawalKey,
        address expectedUser,
        address caller
    );
    error MinimumAmountBelowRequest(
        bytes32 withdrawalKey,
        uint256 requestedMinimum,
        uint256 claimMinimum
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

    event StrategyWithdrawalCompleted(
        address indexed user,
        bytes32 indexed strategyId,
        address indexed asset,
        uint256 shares,
        uint256 amountOut
    );

    event StrategyWithdrawalRequested(
        address indexed user,
        bytes32 indexed strategyId,
        bytes32 indexed withdrawalKey,
        bytes32 adapterRequestId,
        address asset,
        uint256 shares,
        uint256 minimumAmountOut
    );

    event StrategyWithdrawalClaimed(
        address indexed user,
        bytes32 indexed strategyId,
        bytes32 indexed withdrawalKey,
        address asset,
        uint256 shares,
        uint256 amountOut
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

    /// @dev Needed so approved adapters can return native 0G to the vault.
    ///      Direct transfers are accepted but are not credited to user balances.
    receive() external payable {}

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

    /// @notice Withdraw strategy shares back to the caller's idle balance.
    /// @dev Synchronous adapters settle immediately. Asynchronous adapters
    ///      create a pending record that the same user later claims.
    function requestStrategyWithdraw(
        bytes32 strategyId,
        uint256 shares,
        uint256 minAmountOut,
        bytes calldata data
    )
        external
        nonReentrant
        returns (
            bytes32 withdrawalKey,
            uint256 amountOut,
            bool pending
        )
    {
        if (shares == 0) revert ZeroAmount();
        if (minAmountOut == 0) revert ZeroMinAmountOut();

        StrategyManager.StrategyConfig memory config =
            strategyManager.getStrategy(strategyId);

        uint256 availableShares =
            strategySharesOf[msg.sender][strategyId];

        if (availableShares < shares) {
            revert InsufficientUserStrategyShares(
                msg.sender,
                strategyId,
                availableShares,
                shares
            );
        }

        strategySharesOf[msg.sender][strategyId] =
            availableShares - shares;

        IStrategyAdapter adapter =
            IStrategyAdapter(config.adapter);

        uint256 beforeBalance =
            _assetBalance(config.inputAsset);

        bytes32 adapterRequestId;
        (
            adapterRequestId,
            amountOut,
            pending
        ) = adapter.requestWithdraw(
            shares,
            minAmountOut,
            data
        );

        if (pending != config.asynchronous) {
            revert UnexpectedWithdrawalMode(
                strategyId,
                config.asynchronous,
                pending
            );
        }

        uint256 received =
            _assetBalance(config.inputAsset) - beforeBalance;

        if (!pending) {
            _validateWithdrawalReceipt(
                strategyId,
                minAmountOut,
                amountOut,
                received
            );

            idleBalanceOf[msg.sender][config.inputAsset] += received;

            emit StrategyWithdrawalCompleted(
                msg.sender,
                strategyId,
                config.inputAsset,
                shares,
                received
            );

            return (bytes32(0), received, false);
        }

        if (adapterRequestId == bytes32(0)) {
            revert ZeroAdapterRequestId();
        }

        if (amountOut != 0 || received != 0) {
            revert AdapterAmountMismatch(
                strategyId,
                amountOut,
                received
            );
        }

        uint256 nonce = withdrawalNonceOf[msg.sender]++;
        withdrawalKey = keccak256(
            abi.encode(
                address(this),
                block.chainid,
                msg.sender,
                strategyId,
                adapterRequestId,
                nonce
            )
        );

        pendingWithdrawalOf[withdrawalKey] = PendingWithdrawal({
            user: msg.sender,
            strategyId: strategyId,
            adapterRequestId: adapterRequestId,
            asset: config.inputAsset,
            shares: shares,
            minimumAmountOut: minAmountOut,
            active: true
        });

        emit StrategyWithdrawalRequested(
            msg.sender,
            strategyId,
            withdrawalKey,
            adapterRequestId,
            config.inputAsset,
            shares,
            minAmountOut
        );

        return (withdrawalKey, 0, true);
    }

    /// @notice Claim an asynchronous strategy withdrawal into idle balance.
    /// @param minAmountOut Claim-time minimum; may tighten but not lower the
    ///        minimum established by requestStrategyWithdraw().
    function claimStrategyWithdraw(
        bytes32 withdrawalKey,
        uint256 minAmountOut,
        bytes calldata data
    )
        external
        nonReentrant
        returns (uint256 amountOut)
    {
        PendingWithdrawal memory pending =
            pendingWithdrawalOf[withdrawalKey];

        if (!pending.active) {
            revert PendingWithdrawalNotFound(withdrawalKey);
        }

        if (pending.user != msg.sender) {
            revert PendingWithdrawalNotOwned(
                withdrawalKey,
                pending.user,
                msg.sender
            );
        }

        if (minAmountOut < pending.minimumAmountOut) {
            revert MinimumAmountBelowRequest(
                withdrawalKey,
                pending.minimumAmountOut,
                minAmountOut
            );
        }

        StrategyManager.StrategyConfig memory config =
            strategyManager.getStrategy(pending.strategyId);

        if (!config.asynchronous) {
            revert UnexpectedWithdrawalMode(
                pending.strategyId,
                config.asynchronous,
                true
            );
        }

        uint256 beforeBalance =
            _assetBalance(pending.asset);

        uint256 reported = IStrategyAdapter(
            config.adapter
        ).claimWithdraw(
            pending.adapterRequestId,
            minAmountOut,
            data
        );

        uint256 received =
            _assetBalance(pending.asset) - beforeBalance;

        _validateWithdrawalReceipt(
            pending.strategyId,
            minAmountOut,
            reported,
            received
        );

        delete pendingWithdrawalOf[withdrawalKey];

        idleBalanceOf[msg.sender][pending.asset] += received;
        amountOut = received;

        emit StrategyWithdrawalClaimed(
            msg.sender,
            pending.strategyId,
            withdrawalKey,
            pending.asset,
            pending.shares,
            received
        );
    }

    /// @notice Current active underlying value of one user's positions for an asset.
    /// @dev Pending asynchronous withdrawals are excluded until claimed into idle.
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

    function _validateWithdrawalReceipt(
        bytes32 strategyId,
        uint256 minimum,
        uint256 reported,
        uint256 received
    ) private pure {
        if (received < minimum) {
            revert InsufficientWithdrawalAmount(
                strategyId,
                minimum,
                received
            );
        }

        if (reported != received) {
            revert AdapterAmountMismatch(
                strategyId,
                reported,
                received
            );
        }
    }

    function _assetBalance(address asset)
        private
        view
        returns (uint256)
    {
        if (asset == NATIVE_0G) {
            return address(this).balance;
        }

        return IERC20(asset).balanceOf(address(this));
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
