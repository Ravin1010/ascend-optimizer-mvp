// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Address} from "@openzeppelin/contracts/utils/Address.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {IGimoStakePool, IGimoSt0G} from "../interfaces/IGimoStakePool.sol";
import {IStrategyAdapter} from "../interfaces/IStrategyAdapter.sol";

/// @title GimoAdapter
/// @notice Native 0G -> Gimo st0G liquid-staking adapter for AscendVault.
/// @dev Strategy shares are the actual st0G received by this adapter.
///
///      Gimo/st0G is exchange-rate-bearing: staking rewards increase st0G's
///      0G redemption value. Those rewards are therefore reflected through
///      previewRedeem()/totalAssets() and MUST NOT also be notified to
///      RewardAccounting.
///
///      Gimo's protocol withdrawal entry point is parameterless and settles
///      matured requests for the caller. To preserve AscendVault's per-request
///      accounting without accidentally sweeping several users' requests into
///      one claim, this MVP serializes protocol withdrawals: one outstanding
///      Gimo withdrawal is allowed per adapter deployment.
contract GimoAdapter is
    IStrategyAdapter,
    ReentrancyGuard
{
    using Address for address payable;
    using SafeERC20 for IGimoSt0G;

    uint256 public constant RATE_SCALE = 1e18;

    address public immutable vault;
    IGimoStakePool public immutable stakePool;
    IGimoSt0G public immutable st0g;

    string public referral;

    uint256 public withdrawalNonce;
    uint256 public totalPendingWithdrawalAmount;
    bytes32 public activeWithdrawalId;

    mapping(bytes32 requestId => uint256 amount)
        public pendingWithdrawalAmount;

    error ZeroVault();
    error InvalidStakePool(address stakePool);
    error InvalidSt0G(address st0g);
    error OnlyVault(address caller);
    error ZeroAmount();
    error ZeroMinShares();
    error ZeroMinAmountOut();
    error UnexpectedData();
    error InvalidNativeValue(uint256 expected, uint256 received);
    error InvalidRate(uint256 rate);
    error InsufficientShares(uint256 minimum, uint256 received);
    error InsufficientSt0GBalance(uint256 available, uint256 requested);
    error PendingWithdrawalExists(bytes32 requestId);
    error UnknownWithdrawal(bytes32 requestId);
    error InsufficientQueuedAmount(uint256 minimum, uint256 queued);
    error St0GBurnMismatch(uint256 expected, uint256 actual);
    error WithdrawalAmountMismatch(uint256 expected, uint256 received);

    event GimoStaked(
        uint256 amount0G,
        uint256 st0gReceived
    );

    event GimoUnstakeRequested(
        bytes32 indexed requestId,
        uint256 st0gBurned,
        uint256 queued0G
    );

    event GimoWithdrawalClaimed(
        bytes32 indexed requestId,
        uint256 amount0G
    );

    modifier onlyVault() {
        if (msg.sender != vault) {
            revert OnlyVault(msg.sender);
        }
        _;
    }

    constructor(
        address vault_,
        address stakePool_,
        address st0g_,
        string memory referral_
    ) {
        if (vault_ == address(0)) revert ZeroVault();
        if (
            stakePool_ == address(0)
            || stakePool_.code.length == 0
        ) {
            revert InvalidStakePool(stakePool_);
        }
        if (
            st0g_ == address(0)
            || st0g_.code.length == 0
        ) {
            revert InvalidSt0G(st0g_);
        }

        vault = vault_;
        stakePool = IGimoStakePool(stakePool_);
        st0g = IGimoSt0G(st0g_);
        referral = referral_;
    }

    receive() external payable {
        // Gimo withdraw() returns matured native 0G here.
        // Direct transfers are not included in strategy valuation.
    }

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
        return true;
    }

    /// @notice Stake native 0G into Gimo and measure the actual st0G received.
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
        if (data.length != 0) revert UnexpectedData();
        if (amount == 0) revert ZeroAmount();
        if (minShares == 0) revert ZeroMinShares();
        if (msg.value != amount) {
            revert InvalidNativeValue(
                amount,
                msg.value
            );
        }

        uint256 beforeBalance =
            st0g.balanceOf(address(this));

        stakePool.stake{value: amount}(
            referral
        );

        uint256 afterBalance =
            st0g.balanceOf(address(this));

        sharesReceived =
            afterBalance - beforeBalance;

        if (sharesReceived < minShares) {
            revert InsufficientShares(
                minShares,
                sharesReceived
            );
        }

        emit GimoStaked(
            amount,
            sharesReceived
        );
    }

    /// @notice Burn st0G and begin Gimo's delayed native-0G withdrawal.
    /// @dev Gimo's underlying withdraw() aggregates matured requests for the
    ///      caller, so this reference adapter permits only one outstanding
    ///      protocol request at a time.
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
        if (data.length != 0) revert UnexpectedData();
        if (shares == 0) revert ZeroAmount();
        if (minAmountOut == 0) revert ZeroMinAmountOut();

        bytes32 existing = activeWithdrawalId;
        if (existing != bytes32(0)) {
            revert PendingWithdrawalExists(
                existing
            );
        }

        uint256 balance =
            st0g.balanceOf(address(this));

        if (balance < shares) {
            revert InsufficientSt0GBalance(
                balance,
                shares
            );
        }

        uint256 queuedAmount =
            _previewRedeem(shares);

        if (queuedAmount < minAmountOut) {
            revert InsufficientQueuedAmount(
                minAmountOut,
                queuedAmount
            );
        }

        uint256 beforeBalance = balance;

        st0g.forceApprove(
            address(stakePool),
            shares
        );

        stakePool.unstake(shares);

        st0g.forceApprove(
            address(stakePool),
            0
        );

        uint256 afterBalance =
            st0g.balanceOf(address(this));

        uint256 burned =
            beforeBalance - afterBalance;

        if (burned != shares) {
            revert St0GBurnMismatch(
                shares,
                burned
            );
        }

        uint256 nonce = withdrawalNonce++;
        requestId = keccak256(
            abi.encode(
                address(this),
                address(stakePool),
                shares,
                queuedAmount,
                nonce
            )
        );

        activeWithdrawalId = requestId;
        pendingWithdrawalAmount[requestId] =
            queuedAmount;
        totalPendingWithdrawalAmount =
            queuedAmount;

        emit GimoUnstakeRequested(
            requestId,
            shares,
            queuedAmount
        );

        return (
            requestId,
            0,
            true
        );
    }

    /// @notice Claim the currently serialized Gimo withdrawal into AscendVault.
    function claimWithdraw(
        bytes32 requestId,
        uint256 minAmountOut,
        bytes calldata data
    )
        external
        override
        onlyVault
        nonReentrant
        returns (uint256 amountOut)
    {
        if (data.length != 0) revert UnexpectedData();
        if (minAmountOut == 0) revert ZeroMinAmountOut();

        if (
            requestId == bytes32(0)
            || requestId != activeWithdrawalId
        ) {
            revert UnknownWithdrawal(requestId);
        }

        uint256 expected =
            pendingWithdrawalAmount[requestId];

        if (expected == 0) {
            revert UnknownWithdrawal(requestId);
        }

        if (expected < minAmountOut) {
            revert InsufficientQueuedAmount(
                minAmountOut,
                expected
            );
        }

        uint256 beforeBalance =
            address(this).balance;

        // Before maturity Gimo is expected to revert/no-op rather than release
        // usable liquidity. In either case the adapter state remains intact.
        stakePool.withdraw();

        uint256 received =
            address(this).balance
            - beforeBalance;

        if (received != expected) {
            revert WithdrawalAmountMismatch(
                expected,
                received
            );
        }

        delete pendingWithdrawalAmount[requestId];
        activeWithdrawalId = bytes32(0);
        totalPendingWithdrawalAmount = 0;

        payable(vault).sendValue(received);
        amountOut = received;

        emit GimoWithdrawalClaimed(
            requestId,
            amountOut
        );
    }

    /// @notice Underlying native-0G value managed by this Gimo position.
    function totalAssets()
        external
        view
        override
        returns (uint256)
    {
        uint256 activeValue =
            _previewRedeem(
                st0g.balanceOf(address(this))
            );

        return (
            activeValue
            + totalPendingWithdrawalAmount
        );
    }

    /// @notice Current native-0G redemption value of st0G strategy shares.
    function previewRedeem(uint256 shares)
        external
        view
        override
        returns (uint256 amountOut)
    {
        return _previewRedeem(shares);
    }

    function _previewRedeem(uint256 shares)
        private
        view
        returns (uint256 amountOut)
    {
        if (shares == 0) {
            return 0;
        }

        uint256 rate = st0g.getRate();

        if (rate == 0) {
            revert InvalidRate(rate);
        }

        return Math.mulDiv(
            shares,
            rate,
            RATE_SCALE
        );
    }
}
