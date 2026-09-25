// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {V3LiquidityAdapter} from "./V3LiquidityAdapter.sol";

/// @title JaineLPAdapter
/// @notice 0G-mainnet Jaine W0G/USDC.e wrapper over the shared V3 adapter.
/// @dev Factory/router/NPM/token addresses are pinned to the verified Jaine
///      deployment. Pool, fee tier and fixed range remain deployment choices
///      and are validated by V3LiquidityAdapter.
contract JaineLPAdapter is V3LiquidityAdapter {
    address public constant JAINE_FACTORY =
        0x9bdcA5798E52e592A08e3b34d3F18EeF76Af7ef4;

    address public constant JAINE_ROUTER =
        0x8B598A7C136215A95ba0282b4d832B9f9801f2e2;

    address public constant JAINE_POSITION_MANAGER =
        0x8F67A30Ed186e3E1f6504c6dE3239Ef43A2e0d72;

    address public constant W0G =
        0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c;

    address public constant USDCE =
        0x1f3AA82227281cA364bFb3d253B0f1af1Da6473E;

    constructor(
        address vault_,
        address pool_,
        uint24 feeTier_,
        int24 tickLower_,
        int24 tickUpper_,
        uint160 sqrtLowerX96_,
        uint160 sqrtUpperX96_
    )
        V3LiquidityAdapter(
            vault_,
            JAINE_FACTORY,
            JAINE_ROUTER,
            JAINE_POSITION_MANAGER,
            pool_,
            W0G,
            USDCE,
            feeTier_,
            tickLower_,
            tickUpper_,
            sqrtLowerX96_,
            sqrtUpperX96_,
            RouterMode.V1
        )
    {}
}
