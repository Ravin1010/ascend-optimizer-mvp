// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {IStrategyAdapter} from "./interfaces/IStrategyAdapter.sol";

/// @title StrategyManager
/// @notice Registry and hard safety ceiling for Ascend strategy adapters.
/// @dev This contract does not compute APY, risk scores, or portfolio weights.
contract StrategyManager is Ownable2Step {
    uint16 public constant BPS_DENOMINATOR = 10_000;

    struct StrategyConfig {
        address adapter;
        address inputAsset;
        uint256 depositCap;
        uint16 maxAllocationBps;
        bool asynchronous;
        bool active;
    }

    mapping(bytes32 strategyId => StrategyConfig) private _strategies;

    error ZeroStrategyId();
    error InvalidAdapter(address adapter);
    error StrategyAlreadyRegistered(bytes32 strategyId);
    error StrategyNotRegistered(bytes32 strategyId);
    error InvalidAllocationBps(uint256 allocationBps);
    error AdapterAssetMismatch(address expected, address actual);
    error AdapterWithdrawalModeMismatch(bool expected, bool actual);

    event StrategyRegistered(
        bytes32 indexed strategyId,
        address indexed adapter,
        address indexed inputAsset,
        uint256 depositCap,
        uint16 maxAllocationBps,
        bool asynchronous
    );

    event StrategyUpdated(
        bytes32 indexed strategyId,
        uint256 depositCap,
        uint16 maxAllocationBps,
        bool active
    );

    event StrategyAdapterUpdated(
        bytes32 indexed strategyId,
        address indexed oldAdapter,
        address indexed newAdapter
    );

    constructor(address initialOwner) Ownable(initialOwner) {}

    function registerStrategy(
        bytes32 strategyId,
        StrategyConfig calldata config
    ) external onlyOwner {
        if (strategyId == bytes32(0)) revert ZeroStrategyId();
        if (_strategies[strategyId].adapter != address(0)) {
            revert StrategyAlreadyRegistered(strategyId);
        }

        _validateConfig(config);

        _strategies[strategyId] = config;

        emit StrategyRegistered(
            strategyId,
            config.adapter,
            config.inputAsset,
            config.depositCap,
            config.maxAllocationBps,
            config.asynchronous
        );
    }

    function updateLimits(
        bytes32 strategyId,
        uint256 depositCap,
        uint16 maxAllocationBps,
        bool active
    ) external onlyOwner {
        StrategyConfig storage config = _requireStrategy(strategyId);

        if (maxAllocationBps > BPS_DENOMINATOR) {
            revert InvalidAllocationBps(maxAllocationBps);
        }

        config.depositCap = depositCap;
        config.maxAllocationBps = maxAllocationBps;
        config.active = active;

        emit StrategyUpdated(
            strategyId,
            depositCap,
            maxAllocationBps,
            active
        );
    }

    function updateAdapter(
        bytes32 strategyId,
        address newAdapter
    ) external onlyOwner {
        StrategyConfig storage config = _requireStrategy(strategyId);

        if (newAdapter == address(0) || newAdapter.code.length == 0) {
            revert InvalidAdapter(newAdapter);
        }

        _validateAdapterMetadata(
            newAdapter,
            config.inputAsset,
            config.asynchronous
        );

        address oldAdapter = config.adapter;
        config.adapter = newAdapter;

        emit StrategyAdapterUpdated(
            strategyId,
            oldAdapter,
            newAdapter
        );
    }

    function setStrategyActive(
        bytes32 strategyId,
        bool active
    ) external onlyOwner {
        StrategyConfig storage config = _requireStrategy(strategyId);
        config.active = active;

        emit StrategyUpdated(
            strategyId,
            config.depositCap,
            config.maxAllocationBps,
            active
        );
    }

    function getStrategy(bytes32 strategyId)
        external
        view
        returns (StrategyConfig memory)
    {
        StrategyConfig storage config = _requireStrategy(strategyId);
        return config;
    }

    function isStrategyActive(bytes32 strategyId)
        external
        view
        returns (bool)
    {
        StrategyConfig storage config = _strategies[strategyId];
        return config.adapter != address(0) && config.active;
    }

    function _validateConfig(
        StrategyConfig calldata config
    ) private view {
        if (config.adapter == address(0) || config.adapter.code.length == 0) {
            revert InvalidAdapter(config.adapter);
        }

        if (config.maxAllocationBps > BPS_DENOMINATOR) {
            revert InvalidAllocationBps(config.maxAllocationBps);
        }

        _validateAdapterMetadata(
            config.adapter,
            config.inputAsset,
            config.asynchronous
        );
    }

    function _validateAdapterMetadata(
        address adapter,
        address expectedInputAsset,
        bool expectedAsync
    ) private view {
        address actualAsset = IStrategyAdapter(adapter).inputAsset();
        if (actualAsset != expectedInputAsset) {
            revert AdapterAssetMismatch(
                expectedInputAsset,
                actualAsset
            );
        }

        bool actualAsync =
            IStrategyAdapter(adapter).isAsyncWithdrawal();

        if (actualAsync != expectedAsync) {
            revert AdapterWithdrawalModeMismatch(
                expectedAsync,
                actualAsync
            );
        }
    }

    function _requireStrategy(bytes32 strategyId)
        private
        view
        returns (StrategyConfig storage config)
    {
        config = _strategies[strategyId];
        if (config.adapter == address(0)) {
            revert StrategyNotRegistered(strategyId);
        }
    }
}
