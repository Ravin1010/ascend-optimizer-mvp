// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Address} from "@openzeppelin/contracts/utils/Address.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {StrategyManager} from "./StrategyManager.sol";

/// @title RewardAccounting
/// @notice Accumulative reward-per-share accounting for Ascend strategies.
/// @dev Principal/share accounting remains in AscendVault. The vault checkpoints
///      user shares here before every strategy-share balance change.
///
///      Yield already embedded in strategy share value must NOT be notified here.
///      This contract is for separately claimable rewards only.
contract RewardAccounting is Ownable2Step, ReentrancyGuard {
    using Address for address payable;
    using SafeERC20 for IERC20;

    uint256 public constant ACC_PRECISION = 1e18;
    uint256 public constant MAX_REWARD_TOKENS_PER_STRATEGY = 8;
    address public constant NATIVE_0G = address(0);

    address public immutable vault;
    StrategyManager public immutable strategyManager;

    struct UserRewardState {
        uint256 rewardDebt;
        uint256 pending;
    }

    mapping(bytes32 strategyId => uint256)
        public totalStrategyShares;

    mapping(bytes32 strategyId => mapping(address user => uint256))
        public userStrategyShares;

    mapping(bytes32 strategyId => address[])
        private _rewardTokens;

    mapping(bytes32 strategyId => mapping(address rewardToken => bool))
        public rewardTokenRegistered;

    mapping(bytes32 strategyId => mapping(address rewardToken => uint256))
        public accRewardPerShare;

    mapping(
        bytes32 strategyId =>
            mapping(
                address rewardToken =>
                    mapping(address user => UserRewardState)
            )
    ) private _userRewardState;

    error ZeroVault();
    error ZeroStrategyManager();
    error OnlyVault(address caller);
    error UnauthorizedNotifier(address caller, bytes32 strategyId);
    error RewardTokenAlreadyRegistered(bytes32 strategyId, address rewardToken);
    error RewardTokenNotRegistered(bytes32 strategyId, address rewardToken);
    error TooManyRewardTokens(bytes32 strategyId);
    error ZeroAmount();
    error ZeroRecipient();
    error NoStrategyShares(bytes32 strategyId);
    error InvalidNativeValue(uint256 expected, uint256 received);
    error UnexpectedNativeValue(uint256 received);

    event RewardTokenRegistered(
        bytes32 indexed strategyId,
        address indexed rewardToken
    );

    event UserSharesSynced(
        bytes32 indexed strategyId,
        address indexed user,
        uint256 oldShares,
        uint256 newShares
    );

    event RewardNotified(
        bytes32 indexed strategyId,
        address indexed rewardToken,
        address indexed notifier,
        uint256 amount,
        uint256 accRewardPerShare
    );

    event RewardClaimed(
        bytes32 indexed strategyId,
        address indexed rewardToken,
        address indexed user,
        address recipient,
        uint256 amount
    );

    modifier onlyVault() {
        if (msg.sender != vault) {
            revert OnlyVault(msg.sender);
        }
        _;
    }

    constructor(
        address initialOwner,
        address vault_,
        address strategyManager_
    ) Ownable(initialOwner) {
        if (vault_ == address(0)) revert ZeroVault();
        if (strategyManager_ == address(0)) {
            revert ZeroStrategyManager();
        }

        vault = vault_;
        strategyManager = StrategyManager(strategyManager_);
    }

    receive() external payable {}

    /// @notice Register one separately claimable reward token for a strategy.
    /// @dev address(0) represents native 0G.
    function registerRewardToken(
        bytes32 strategyId,
        address rewardToken
    ) external onlyOwner {
        strategyManager.getStrategy(strategyId);

        if (rewardTokenRegistered[strategyId][rewardToken]) {
            revert RewardTokenAlreadyRegistered(strategyId, rewardToken);
        }

        if (
            _rewardTokens[strategyId].length
                >= MAX_REWARD_TOKENS_PER_STRATEGY
        ) {
            revert TooManyRewardTokens(strategyId);
        }

        rewardTokenRegistered[strategyId][rewardToken] = true;
        _rewardTokens[strategyId].push(rewardToken);

        emit RewardTokenRegistered(strategyId, rewardToken);
    }

    function rewardTokens(bytes32 strategyId)
        external
        view
        returns (address[] memory)
    {
        return _rewardTokens[strategyId];
    }

    /// @notice Checkpoint accrued entitlement before a vault share change.
    function syncUserShares(
        address user,
        bytes32 strategyId,
        uint256 newShares
    ) external onlyVault {
        uint256 oldShares =
            userStrategyShares[strategyId][user];

        address[] storage tokens =
            _rewardTokens[strategyId];

        for (uint256 i = 0; i < tokens.length; ++i) {
            _checkpoint(
                user,
                strategyId,
                tokens[i],
                oldShares,
                newShares
            );
        }

        totalStrategyShares[strategyId] =
            totalStrategyShares[strategyId]
            - oldShares
            + newShares;

        userStrategyShares[strategyId][user] = newShares;

        emit UserSharesSynced(
            strategyId,
            user,
            oldShares,
            newShares
        );
    }

    /// @notice Add separately claimable rewards to a strategy.
    /// @dev Callable only by the current registered adapter or contract owner.
    function notifyReward(
        bytes32 strategyId,
        address rewardToken,
        uint256 amount
    )
        external
        payable
        nonReentrant
        returns (uint256 creditedAmount)
    {
        if (!rewardTokenRegistered[strategyId][rewardToken]) {
            revert RewardTokenNotRegistered(strategyId, rewardToken);
        }
        if (amount == 0) revert ZeroAmount();

        StrategyManager.StrategyConfig memory config =
            strategyManager.getStrategy(strategyId);

        if (
            msg.sender != owner()
            && msg.sender != config.adapter
        ) {
            revert UnauthorizedNotifier(msg.sender, strategyId);
        }

        uint256 shares = totalStrategyShares[strategyId];
        if (shares == 0) {
            revert NoStrategyShares(strategyId);
        }

        if (rewardToken == NATIVE_0G) {
            if (msg.value != amount) {
                revert InvalidNativeValue(amount, msg.value);
            }
            creditedAmount = amount;
        } else {
            if (msg.value != 0) {
                revert UnexpectedNativeValue(msg.value);
            }

            IERC20 token = IERC20(rewardToken);
            uint256 beforeBalance =
                token.balanceOf(address(this));

            token.safeTransferFrom(
                msg.sender,
                address(this),
                amount
            );

            creditedAmount =
                token.balanceOf(address(this))
                - beforeBalance;

            if (creditedAmount == 0) {
                revert ZeroAmount();
            }
        }

        accRewardPerShare[strategyId][rewardToken] +=
            Math.mulDiv(
                creditedAmount,
                ACC_PRECISION,
                shares
            );

        emit RewardNotified(
            strategyId,
            rewardToken,
            msg.sender,
            creditedAmount,
            accRewardPerShare[strategyId][rewardToken]
        );
    }

    /// @notice Claim one reward token for a user through AscendVault.
    function claimFor(
        address user,
        bytes32 strategyId,
        address rewardToken,
        address payable recipient
    )
        external
        onlyVault
        nonReentrant
        returns (uint256 amount)
    {
        if (recipient == address(0)) revert ZeroRecipient();

        if (!rewardTokenRegistered[strategyId][rewardToken]) {
            revert RewardTokenNotRegistered(strategyId, rewardToken);
        }

        uint256 shares =
            userStrategyShares[strategyId][user];

        _checkpoint(
            user,
            strategyId,
            rewardToken,
            shares,
            shares
        );

        UserRewardState storage state =
            _userRewardState[strategyId][rewardToken][user];

        amount = state.pending;
        state.pending = 0;

        if (amount != 0) {
            if (rewardToken == NATIVE_0G) {
                recipient.sendValue(amount);
            } else {
                IERC20(rewardToken).safeTransfer(
                    recipient,
                    amount
                );
            }
        }

        emit RewardClaimed(
            strategyId,
            rewardToken,
            user,
            recipient,
            amount
        );
    }

    function claimable(
        address user,
        bytes32 strategyId,
        address rewardToken
    ) external view returns (uint256 amount) {
        UserRewardState storage state =
            _userRewardState[strategyId][rewardToken][user];

        uint256 shares =
            userStrategyShares[strategyId][user];

        uint256 accumulated = Math.mulDiv(
            shares,
            accRewardPerShare[strategyId][rewardToken],
            ACC_PRECISION
        );

        amount = state.pending;

        if (accumulated > state.rewardDebt) {
            amount += accumulated - state.rewardDebt;
        }
    }

    function userRewardState(
        address user,
        bytes32 strategyId,
        address rewardToken
    )
        external
        view
        returns (uint256 rewardDebt, uint256 pending)
    {
        UserRewardState storage state =
            _userRewardState[strategyId][rewardToken][user];

        return (
            state.rewardDebt,
            state.pending
        );
    }

    function _checkpoint(
        address user,
        bytes32 strategyId,
        address rewardToken,
        uint256 oldShares,
        uint256 newShares
    ) private {
        UserRewardState storage state =
            _userRewardState[strategyId][rewardToken][user];

        uint256 acc =
            accRewardPerShare[strategyId][rewardToken];

        uint256 accumulated = Math.mulDiv(
            oldShares,
            acc,
            ACC_PRECISION
        );

        if (accumulated > state.rewardDebt) {
            state.pending +=
                accumulated - state.rewardDebt;
        }

        state.rewardDebt = Math.mulDiv(
            newShares,
            acc,
            ACC_PRECISION
        );
    }
}
