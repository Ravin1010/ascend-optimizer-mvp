// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Address} from "@openzeppelin/contracts/utils/Address.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

import {IRestakingConnector} from "../interfaces/IRestakingConnector.sol";
import {IStrategyAdapter} from "../interfaces/IStrategyAdapter.sol";

/// @title RestakingAdapter
/// @notice Protocol-agnostic restaking boundary for AscendVault.
/// @dev The adapter is deliberately fixed to one connector at deployment.
///      Concrete Symbiotic/0G or other protocol calls belong in a separately
///      verified connector implementation. The optimizer never calls either
///      contract directly.
///
///      Protocol-specific data may be forwarded only to this immutable connector;
///      there is no arbitrary target address or generic call primitive.
contract RestakingAdapter is IStrategyAdapter, ReentrancyGuard {
    using Address for address payable;
    using SafeERC20 for IERC20;

    address public constant NATIVE_0G = address(0);

    address public immutable vault;
    IRestakingConnector public immutable connector;
    address public immutable restakingAsset;
    bool public immutable asynchronous;

    mapping(bytes32 requestId => bool)
        public pendingWithdrawal;

    error ZeroVault();
    error InvalidConnector(address connector);
    error ConnectorAssetMismatch(address expected, address actual);
    error ConnectorWithdrawalModeMismatch(bool expected, bool actual);
    error OnlyVault(address caller);
    error ZeroAmount();
    error ZeroMinShares();
    error ZeroMinAmountOut();
    error InvalidNativeValue(uint256 expected, uint256 received);
    error UnexpectedNativeValue(uint256 received);
    error InsufficientShares(uint256 minimum, uint256 received);
    error UnexpectedWithdrawalMode(bool expectedAsync, bool actualPending);
    error ZeroRequestId();
    error DuplicateWithdrawal(bytes32 requestId);
    error UnknownWithdrawal(bytes32 requestId);
    error InsufficientWithdrawalAmount(uint256 minimum, uint256 received);
    error ConnectorAmountMismatch(uint256 reported, uint256 received);

    event Restaked(
        uint256 amount,
        uint256 sharesReceived
    );

    event RestakingWithdrawalRequested(
        bytes32 indexed requestId,
        uint256 shares
    );

    event RestakingWithdrawalCompleted(
        bytes32 indexed requestId,
        uint256 amountOut
    );

    modifier onlyVault() {
        if (msg.sender != vault) {
            revert OnlyVault(msg.sender);
        }
        _;
    }

    constructor(
        address vault_,
        address connector_,
        address expectedAsset,
        bool expectedAsync
    ) {
        if (vault_ == address(0)) revert ZeroVault();
        if (
            connector_ == address(0)
            || connector_.code.length == 0
        ) {
            revert InvalidConnector(connector_);
        }

        IRestakingConnector connectorContract =
            IRestakingConnector(connector_);

        address actualAsset =
            connectorContract.inputAsset();

        if (actualAsset != expectedAsset) {
            revert ConnectorAssetMismatch(
                expectedAsset,
                actualAsset
            );
        }

        bool actualAsync =
            connectorContract.isAsyncWithdrawal();

        if (actualAsync != expectedAsync) {
            revert ConnectorWithdrawalModeMismatch(
                expectedAsync,
                actualAsync
            );
        }

        vault = vault_;
        connector = connectorContract;
        restakingAsset = expectedAsset;
        asynchronous = expectedAsync;
    }

    receive() external payable {}

    function inputAsset()
        external
        view
        override
        returns (address)
    {
        return restakingAsset;
    }

    function isAsyncWithdrawal()
        external
        view
        override
        returns (bool)
    {
        return asynchronous;
    }

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
        if (amount == 0) revert ZeroAmount();
        if (minShares == 0) revert ZeroMinShares();

        if (restakingAsset == NATIVE_0G) {
            if (msg.value != amount) {
                revert InvalidNativeValue(
                    amount,
                    msg.value
                );
            }

            sharesReceived =
                connector.deposit{value: amount}(
                    amount,
                    minShares,
                    data
                );
        } else {
            if (msg.value != 0) {
                revert UnexpectedNativeValue(msg.value);
            }

            IERC20 token = IERC20(restakingAsset);

            token.safeTransferFrom(
                msg.sender,
                address(this),
                amount
            );

            token.forceApprove(
                address(connector),
                amount
            );

            sharesReceived = connector.deposit(
                amount,
                minShares,
                data
            );

            token.forceApprove(
                address(connector),
                0
            );
        }

        if (sharesReceived < minShares) {
            revert InsufficientShares(
                minShares,
                sharesReceived
            );
        }

        emit Restaked(
            amount,
            sharesReceived
        );
    }

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
        if (shares == 0) revert ZeroAmount();
        if (minAmountOut == 0) revert ZeroMinAmountOut();

        uint256 beforeBalance =
            _assetBalance();

        (
            requestId,
            amountOut,
            pending
        ) = connector.requestWithdraw(
            shares,
            minAmountOut,
            data
        );

        if (pending != asynchronous) {
            revert UnexpectedWithdrawalMode(
                asynchronous,
                pending
            );
        }

        uint256 received =
            _assetBalance() - beforeBalance;

        if (!pending) {
            _validateReceipt(
                minAmountOut,
                amountOut,
                received
            );

            _sendToVault(received);

            emit RestakingWithdrawalCompleted(
                bytes32(0),
                received
            );

            return (
                bytes32(0),
                received,
                false
            );
        }

        if (requestId == bytes32(0)) {
            revert ZeroRequestId();
        }
        if (pendingWithdrawal[requestId]) {
            revert DuplicateWithdrawal(requestId);
        }
        if (amountOut != 0 || received != 0) {
            revert ConnectorAmountMismatch(
                amountOut,
                received
            );
        }

        pendingWithdrawal[requestId] = true;

        emit RestakingWithdrawalRequested(
            requestId,
            shares
        );

        return (requestId, 0, true);
    }

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
        if (minAmountOut == 0) revert ZeroMinAmountOut();
        if (!pendingWithdrawal[requestId]) {
            revert UnknownWithdrawal(requestId);
        }

        uint256 beforeBalance =
            _assetBalance();

        uint256 reported =
            connector.claimWithdraw(
                requestId,
                minAmountOut,
                data
            );

        uint256 received =
            _assetBalance() - beforeBalance;

        _validateReceipt(
            minAmountOut,
            reported,
            received
        );

        delete pendingWithdrawal[requestId];

        _sendToVault(received);
        amountOut = received;

        emit RestakingWithdrawalCompleted(
            requestId,
            amountOut
        );
    }

    function totalAssets()
        external
        view
        override
        returns (uint256)
    {
        return connector.totalAssets();
    }

    function previewRedeem(uint256 shares)
        external
        view
        override
        returns (uint256 amountOut)
    {
        return connector.previewRedeem(shares);
    }

    function _assetBalance()
        private
        view
        returns (uint256)
    {
        if (restakingAsset == NATIVE_0G) {
            return address(this).balance;
        }

        return IERC20(restakingAsset).balanceOf(
            address(this)
        );
    }

    function _sendToVault(uint256 amount)
        private
    {
        if (restakingAsset == NATIVE_0G) {
            payable(vault).sendValue(amount);
        } else {
            IERC20(restakingAsset).safeTransfer(
                vault,
                amount
            );
        }
    }

    function _validateReceipt(
        uint256 minimum,
        uint256 reported,
        uint256 received
    )
        private
        pure
    {
        if (received < minimum) {
            revert InsufficientWithdrawalAmount(
                minimum,
                received
            );
        }

        if (reported != received) {
            revert ConnectorAmountMismatch(
                reported,
                received
            );
        }
    }
}
