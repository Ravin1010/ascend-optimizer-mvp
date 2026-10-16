#!/usr/bin/env node
"use strict";
const {JsonRpcProvider,FetchRequest}=require("ethers");
const {publicPreview}=require("./controlled-executor");
const ALLOWED=new Set(["eth_chainId","eth_getBalance","eth_getTransactionCount","eth_getBlockByNumber","eth_gasPrice","eth_maxPriorityFeePerGas","eth_call","eth_estimateGas","eth_getCode","eth_getTransactionByHash","eth_getTransactionReceipt","eth_blockNumber"]);
function assertReadonly(payload) {
  for(const request of Array.isArray(payload)?payload:[payload]) if(!ALLOWED.has(request.method)) throw Error("STOP: signing/submission RPC forbidden");
}
class ReadonlyProvider extends JsonRpcProvider {
  async _send(payload) {assertReadonly(payload);return super._send(payload);}
}
async function main() {
  if(process.argv.length>2) throw Error("STOP: no execution flags supported; read-only preview only");
  const request=new FetchRequest("https://evmrpc-testnet.0g.ai");request.timeout=30000;
  const proxy=process.env.HTTPS_PROXY || process.env.https_proxy;
  if(proxy){const {HttpsProxyAgent}=require("https-proxy-agent");request.getUrlFunc=FetchRequest.createGetUrlFunc({agent:new HttpsProxyAgent(proxy)});}
  const provider=new ReadonlyProvider(request,{chainId:16602,name:"galileo"},{staticNetwork:true,batchMaxCount:1});
  try {console.log(JSON.stringify(await publicPreview(provider),null,2));}finally{provider.destroy();}
}
if(require.main===module)main().catch(()=>{console.error("STOP: read-only funding preview failed; no signer or public transaction submission is available.");process.exitCode=1;});
module.exports={assertReadonly,ReadonlyProvider};
