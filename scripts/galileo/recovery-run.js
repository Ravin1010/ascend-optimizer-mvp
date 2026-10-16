#!/usr/bin/env node
"use strict";
const {FetchRequest}=require("ethers");
const {ReadonlyProvider}=require("./controlled-preview");
const {ExecutionProvider}=require("./execution-provider");
const {identity}=require("./release-integrity");
const {recoveryAuthorization}=require("./recovery-policy");
const {publicRecovery,recoverySourceState}=require("./recovery-release");
async function main() {
  const args=process.argv.slice(2);
  if(args.length===1&&args[0]==="--inspect") {
    const i=identity();console.log(JSON.stringify({mode:"RECOVERY_IDENTITY_ONLY_NOT_AUTHORIZATION",...recoverySourceState(),plan:i.planHash,artifacts:i.artifactHash},null,2));return;
  }
  const a=recoveryAuthorization(args,process.env);
  const req=new FetchRequest("https://evmrpc-testnet.0g.ai");req.timeout=30000;
  const proxy=process.env.HTTPS_PROXY||process.env.https_proxy;
  if(proxy){const {HttpsProxyAgent}=require("https-proxy-agent");req.getUrlFunc=FetchRequest.createGetUrlFunc({agent:new HttpsProxyAgent(proxy)});}
  const Provider=a.mode==="BROADCAST"?ExecutionProvider:ReadonlyProvider;
  const provider=new Provider(req,{chainId:16602,name:"galileo"},{staticNetwork:true,batchMaxCount:1});
  try {
    const result=await publicRecovery({args,env:process.env,provider});
    console.log(JSON.stringify(a.mode==="BROADCAST"?{status:"RECOVERY_EXECUTION_COMPLETED",confirmedTransactions:result.journal.receipts.length}:result,null,2));
  }finally{provider.destroy();}
}
if(require.main===module)main().catch(()=>{console.error("STOP: recovery authorization/validation/execution failed; preserve both journals and inspect public evidence. No automatic retry.");process.exitCode=2;});
module.exports={main};
