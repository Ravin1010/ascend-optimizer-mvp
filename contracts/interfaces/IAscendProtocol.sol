// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {IERC4626} from "@openzeppelin/contracts/interfaces/IERC4626.sol";

/// @notice Minimal live Ascend/Mellow SourceCore surface used by the adapter.
interface IAscendSourceCore is IERC4626 {
    function requestWithdrawal(uint256 shares) external;

    function withdrawalQueue()
        external
        view
        returns (address);

    function oftAdapter()
        external
        view
        returns (address);
}

/// @notice Minimal Mellow withdrawal-queue surface used by the adapter.
interface IAscendWithdrawalQueue {
    function sourceCore()
        external
        view
        returns (address);

    function asset()
        external
        view
        returns (address);

    function currentEpoch()
        external
        view
        returns (uint256);

    function epochDuration()
        external
        view
        returns (uint256);

    function withdrawalDelay()
        external
        view
        returns (uint256);

    function sharesOf(
        uint256 epoch,
        address account
    )
        external
        view
        returns (uint256);

    function claim(
        uint256 epoch,
        address receiver
    )
        external
        returns (uint256 assets);
}

/// @notice Wrapped native 0G surface.
interface IAscendW0G is IERC20 {
    function deposit() external payable;

    function withdraw(uint256 amount) external;
}
