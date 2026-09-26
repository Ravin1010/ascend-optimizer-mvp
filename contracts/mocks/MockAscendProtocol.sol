// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

contract MockAscendW0G is ERC20 {
    constructor() ERC20("Wrapped 0G", "W0G") {}

    receive() external payable {
        deposit();
    }

    function deposit() public payable {
        _mint(msg.sender, msg.value);
    }

    function withdraw(uint256 amount) external {
        _burn(msg.sender, amount);
        payable(msg.sender).transfer(amount);
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract MockAscendSourceCore;

contract MockAscendWithdrawalQueue {
    using SafeERC20 for IERC20;

    MockAscendSourceCore public immutable sourceCore;
    IERC20 public immutable asset;

    uint256 public currentEpoch;
    uint256 public epochDuration = 7 days;
    uint256 public withdrawalDelay = 7 days;

    bool public ready;

    mapping(uint256 => mapping(address => uint256))
        public sharesOf;

    mapping(uint256 => uint256)
        public totalSharesByEpoch;

    constructor(
        address sourceCore_,
        address asset_
    ) {
        sourceCore = MockAscendSourceCore(sourceCore_);
        asset = IERC20(asset_);
    }

    function setReady(bool ready_) external {
        ready = ready_;
    }

    function setCurrentEpoch(uint256 epoch_) external {
        currentEpoch = epoch_;
    }

    function request(
        address account,
        uint256 shares
    ) external {
        require(msg.sender == address(sourceCore), "source only");

        sharesOf[currentEpoch][account] += shares;
        totalSharesByEpoch[currentEpoch] += shares;
    }

    function claim(
        uint256 epoch,
        address receiver
    )
        external
        returns (uint256 assets)
    {
        if (!ready) return 0;

        uint256 shares =
            sharesOf[epoch][msg.sender];

        if (shares == 0) return 0;

        delete sharesOf[epoch][msg.sender];

        assets = sourceCore.previewRedeem(
            shares
        );

        sourceCore.releaseToQueue(
            address(this),
            shares,
            assets
        );

        asset.safeTransfer(
            receiver,
            assets
        );
    }
}

contract MockAscendSourceCore is ERC20 {
    using SafeERC20 for IERC20;

    IERC20 public immutable assetToken;
    MockAscendWithdrawalQueue public withdrawalQueueContract;

    uint256 public rate = 1e18;

    constructor(address asset_)
        ERC20("Ascend Staked 0G", "a0G")
    {
        assetToken = IERC20(asset_);
    }

    function setWithdrawalQueue(address queue_) external {
        require(address(withdrawalQueueContract) == address(0), "set");
        withdrawalQueueContract = MockAscendWithdrawalQueue(queue_);
    }

    function asset() external view returns (address) {
        return address(assetToken);
    }

    function withdrawalQueue() external view returns (address) {
        return address(withdrawalQueueContract);
    }

    function oftAdapter() external pure returns (address) {
        return address(0x1234);
    }

    function setRate(uint256 rate_) external {
        require(rate_ != 0, "rate");
        rate = rate_;
    }

    function deposit(
        uint256 assets,
        address receiver
    )
        external
        returns (uint256 shares)
    {
        shares = Math.mulDiv(
            assets,
            1e18,
            rate
        );

        assetToken.safeTransferFrom(
            msg.sender,
            address(this),
            assets
        );

        _mint(
            receiver,
            shares
        );
    }

    function previewRedeem(uint256 shares)
        public
        view
        returns (uint256 assets)
    {
        return Math.mulDiv(
            shares,
            rate,
            1e18
        );
    }

    function requestWithdrawal(uint256 shares) external {
        _transfer(
            msg.sender,
            address(withdrawalQueueContract),
            shares
        );

        withdrawalQueueContract.request(
            msg.sender,
            shares
        );
    }

    function releaseToQueue(
        address queue,
        uint256 shares,
        uint256 assets
    ) external {
        require(msg.sender == address(withdrawalQueueContract), "queue only");

        _burn(
            queue,
            shares
        );

        assetToken.safeTransfer(
            queue,
            assets
        );
    }

    function balanceOf(address account)
        public
        view
        override
        returns (uint256)
    {
        return super.balanceOf(account);
    }
}
