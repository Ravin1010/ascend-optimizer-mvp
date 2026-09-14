// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title A0GToken
/// @notice Non-rebasing reference LST for the Ascend capstone.
/// @dev a0G is the Ascend LST concept. It is not A0GI.
contract A0GToken is ERC20, AccessControl {
    bytes32 public constant ISSUER_ROLE = keccak256("ISSUER_ROLE");

    constructor(
        address initialAdmin,
        address ascendStakingAdapter
    ) ERC20("Ascend 0G", "a0G") {
        if (initialAdmin == address(0)) {
            revert AccessControlInvalidDefaultAdmin(address(0));
        }
        if (ascendStakingAdapter == address(0)) {
            revert AccessControlUnauthorizedAccount(
                address(0),
                ISSUER_ROLE
            );
        }

        _grantRole(DEFAULT_ADMIN_ROLE, initialAdmin);
        _grantRole(ISSUER_ROLE, ascendStakingAdapter);
    }

    /// @notice Mint a0G principal when 0G enters Ascend staking.
    function mint(
        address to,
        uint256 amount
    ) external onlyRole(ISSUER_ROLE) {
        _mint(to, amount);
    }

    /// @notice Burn a0G principal when the managed staking position is redeemed.
    function burn(
        address from,
        uint256 amount
    ) external onlyRole(ISSUER_ROLE) {
        _burn(from, amount);
    }
}
