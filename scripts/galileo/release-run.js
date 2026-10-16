#!/usr/bin/env node
"use strict";
const {FetchRequest}=require("ethers");
const {ReadonlyProvider}=require("./controlled-preview");
const {ExecutionProvider}=require("./execution-provider");
const {authorize,authorizeReview}=require("./release-policy");
const {identity}=require("./release-integrity");
const {publicExecution}=require("./controlled-executor");
async function main(){
  const args=process.argv.slice(2);
  if(args.length===1&&args[0]==="--inspect"){
    const i=identity();console.log(JSON.stringify({mode:"IDENTITY_ONLY_NOT_AUTHORIZATION",...i.state,plan:i.planHash,artifacts:i.artifactHash,broadcastCapable:true},null,2));return;
  }
  const reviewOnly=args.includes("--review-only");
  if(reviewOnly)authorizeReview(args);else authorize(args,process.env);
  const req=new FetchRequest("https://evmrpc-testnet.0g.ai");req.timeout=30000;
  const proxy=process.env.HTTPS_PROXY||process.env.https_proxy;
  if(proxy){const {HttpsProxyAgent}=require("https-proxy-agent");req.getUrlFunc=FetchRequest.createGetUrlFunc({agent:new HttpsProxyAgent(proxy)});}
  const Provider=reviewOnly?ReadonlyProvider:ExecutionProvider;
  const provider=new Provider(req,{chainId:16602,name:"galileo"},{staticNetwork:true,batchMaxCount:1});
  try{
    const result=await publicExecution({args,env:process.env,provider});
    if(reviewOnly)console.log(JSON.stringify(result,null,2));
    else console.log(JSON.stringify({status:result.status||"COMPLETED",confirmedTransactions:result.journal?.receipts.length,chainId:16602},null,2));
  }finally{provider.destroy();}
}
if(require.main===module)main().catch(()=>{console.error("STOP: authorization/readiness/execution failed. No secrets are logged; inspect public receipt evidence before any retry.");process.exitCode=2;});
module.exports={main};
