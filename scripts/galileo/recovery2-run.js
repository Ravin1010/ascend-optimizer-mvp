#!/usr/bin/env node
"use strict";
const {FetchRequest}=require("ethers");
const {ReadonlyProvider}=require("./controlled-preview"),{ExecutionProvider}=require("./execution-provider");
const {identity}=require("./release-integrity"),{recoverySourceState}=require("./recovery-release");
const {stage2Authorization}=require("./recovery2-policy"),{publicStage2}=require("./recovery2-release");
async function main(){
  const args=process.argv.slice(2);
  if(args.length===1&&args[0]==="--inspect"){const i=identity();console.log(JSON.stringify({mode:"STAGE2_IDENTITY_ONLY_NOT_AUTHORIZATION",...recoverySourceState(),plan:i.planHash,artifacts:i.artifactHash},null,2));return;}
  const a=stage2Authorization(args,process.env),request=new FetchRequest("https://evmrpc-testnet.0g.ai");request.timeout=30000;
  const proxy=process.env.HTTPS_PROXY||process.env.https_proxy;
  if(proxy){const {HttpsProxyAgent}=require("https-proxy-agent");request.getUrlFunc=FetchRequest.createGetUrlFunc({agent:new HttpsProxyAgent(proxy)});}
  const Provider=a.mode==="BROADCAST"?ExecutionProvider:ReadonlyProvider,p=new Provider(request,{chainId:16602,name:"galileo"},{staticNetwork:true,batchMaxCount:1});
  try{const r=await publicStage2({args,env:process.env,provider:p});console.log(JSON.stringify(a.mode==="BROADCAST"?{status:"RECOVERY2_EXECUTION_COMPLETED",confirmedTransactions:r.journal.receipts.length}:r,null,2));}finally{p.destroy();}
}
if(require.main===module)main().catch(error=>{console.error(error.phase?`STOP: Stage-2 ${error.phase} failed; preserve all journals; no retry`:"STOP: Stage-2 authorization/identity failed; no retry");process.exitCode=2;});
module.exports={main};
