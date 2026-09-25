// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {V3LiquidityAdapter} from "./V3LiquidityAdapter.sol";

/// @title OkuV3Adapter
/// @notice Oku-facing Uniswap V3 W0G/USDC.e wrapper for 0G.
/// @dev Oku is the frontend; execution occurs against the underlying V3
///      deployment. The factory and Router02 addresses already used by the live
///      collector are pinned here. The NPM is supplied at deployment and the
///      base constructor rejects it unless npm.factory() equals the pinned
///      factory, avoiding an unverified hard-coded NPM assumption.
contract OkuV3Adapter is V3LiquidityAdapter {
    address public constant UNISWAP_V3_FACTORY =
        0xcb2436774C3e191c85056d248EF4260ce5f27A9D;

    address public constant SWAP_ROUTER_02 =
        0x807F4E281B7A3B324825C64ca53c69F0b418dE40;

    address public constant W0G =
        0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c;

    address public constant USDCE =
        0x1f3AA82227281cA364bFb3d253B0f1af1Da6473E;

    constructor(
        address vault_,
        address positionManager_,
        address pool_,
        uint24 feeTier_,
        int24 tickLower_,
        int24 tickUpper_,
        uint160 sqrtLowerX96_,
        uint160 sqrtUpperX96_
    )
        V3LiquidityAdapter(
            DeploymentConfig({
                vault: vault_,
                factory: UNISWAP_V3_FACTORY,
                router: SWAP_ROUTER_02,
                positionManager: positionManager_,
                pool: pool_,
                w0g: W0G,
                usdce: USDCE,
                feeTier: feeTier_,
                tickLower: tickLower_,
                tickUpper: tickUpper_,
                sqrtLowerX96: sqrtLowerX96_,
                sqrtUpperX96: sqrtUpperX96_,
                routerMode: RouterMode.ROUTER02
            })
        )
    {}
}
