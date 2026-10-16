// No signer loading here: even preflight must never inspect a private key.
const base = require("./hardhat.config");
module.exports = {
  ...base,
  solidity: {
    ...base.solidity,
    settings: { ...base.solidity.settings, evmVersion: "cancun" }
  },
  paths: {
    ...base.paths,
    tests: "./test-galileo",
    artifacts: "./artifacts-galileo",
    cache: "./cache-galileo"
  },
  networks: {
    hardhat: { chainId: 31337 },
    galileo: {
      url: process.env.GALILEO_RPC_URL || "https://evmrpc-testnet.0g.ai",
      chainId: 16602,
      accounts: []
    }
  }
};
