#!/usr/bin/env node
"use strict";
const {FetchRequest}=require("ethers");
const {ReadonlyProvider}=require("./controlled-preview");
const {authorize}=require("./release-policy");
const {identity}=require("./release-integrity");
const {publicExecution}=require("./controlled-executor");
async function main() {
  const args=process.argv.slice(2);
  if(args.length===1&&args[0]==="--inspect"){
    const i=identity();console.log(JSON.stringify({mode:"IDENTITY_ONLY_NOT_AUTHORIZATION",...i.state,plan:i.planHash,artifacts:i.artifactHash,publicSubmissionEnabled:false},null,2));return;
  }
  authorize(args,process.env); // acknowledgement only, never secret/environment enumeration
  const req=new FetchRequest("https://evmrpc-testnet.0g.ai");req.timeout=30000;
  const proxy=process.env.HTTPS_PROXY||process.env.https_proxy;
  if(proxy){const {HttpsProxyAgent}=require("https-proxy-agent");req.getUrlFunc=FetchRequest.createGetUrlFunc({agent:new HttpsProxyAgent(proxy)});}
  const provider=new ReadonlyProvider(req,{chainId:16602,name:"galileo"},{staticNetwork:true,batchMaxCount:1});
  try{await publicExecution({args,env:process.env,provider});}finally{provider.destroy();}
}
if(require.main===module)main().catch(error=>{
  if(error.code==="SEPARATE_USER_APPROVAL_REQUIRED")console.log(JSON.stringify({barrier:error.message,...error.readiness},null,2));
  else console.error("STOP: release review failed before signer access; check public configuration/integrity/readiness. No signing or submission is available.");
  // Reaching the final barrier is still a refusal to execute, not success/authorization.
  process.exitCode=2;
});
module.exports={main};
