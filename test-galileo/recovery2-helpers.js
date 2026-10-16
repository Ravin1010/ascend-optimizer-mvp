"use strict";
const hre=require("hardhat"),fs=require("node:fs"),os=require("node:os"),path=require("node:path");
const {Interface,ZeroAddress}=require("ethers");
const originalBytes=require("./recovery-fixture"),stage1Bytes=require("./recovery2-fixture");
const {ORIGINAL}=require("../scripts/galileo/recovery-policy"),{S2}=require("../scripts/galileo/recovery2-policy");
const {controlledPlan}=require("../scripts/galileo/controlled-plan");
const {loadArtifacts}=require("../scripts/galileo/release-integrity");
const {engine}=require("../scripts/galileo/controlled-executor");
const {readPredecessors}=require("../scripts/galileo/recovery2-validator");
let bundle,localState,localPrefix,localSnapshot,codes;
async function setup(){
 bundle=loadArtifacts();await hre.network.provider.send("hardhat_reset");
 await hre.network.provider.send("hardhat_setBalance",[ORIGINAL.actor,"0x"+BigInt(ORIGINAL.initialBalanceWei).toString(16)]);
 await hre.network.provider.send("hardhat_impersonateAccount",[ORIGINAL.actor]);
 const signer=await hre.ethers.getSigner(ORIGINAL.actor);let value=null;const store={load:()=>structuredClone(value),save:j=>{value=structuredClone(j);}};
 const prefix=await engine({provider:hre.ethers.provider,signer,actor:ORIGINAL.actor,bundle,review:controlledPlan(),sourceCommit:"local-stage2-prefix",store,maxSteps:23,expectedChain:31337,mode:"LOCAL_ONLY"});
 localState=prefix.state;localPrefix=prefix.journal;localSnapshot=await hre.network.provider.send("evm_snapshot");
 codes=new Map();for(const name of Object.keys(localState.artifactNames))codes.set(localState[name].toLowerCase(),await hre.ethers.provider.getCode(localState[name]));
}
function fixture(mode=S2.replay){
 const original=JSON.parse(originalBytes()),stage1=JSON.parse(stage1Bytes()),review=controlledPlan(),now=Math.floor(Date.now()/1000);
 const transactions=new Map(stage1.receipts.map(r=>[r.transactionHash,{hash:r.transactionHash,from:ORIGINAL.actor,nonce:r.nonce,to:r.target,data:r.calldata,value:BigInt(r.valueWei),gasLimit:BigInt(r.gasLimit),gasPrice:BigInt(r.effectiveGasPrice),chainId:16602n}]));
 const receipts=new Map(stage1.receipts.map(r=>[r.transactionHash,{hash:r.transactionHash,status:1,blockHash:r.blockHash,blockNumber:r.blockNumber,contractAddress:r.deployedAddress,gasUsed:BigInt(r.gasUsed),gasPrice:BigInt(r.effectiveGasPrice)}]));
 const blocks=new Map(stage1.receipts.map(r=>[r.blockNumber,{number:r.blockNumber,hash:r.blockHash,timestamp:now-60}]));
 const interfaces=new Map();for(const [name,artifact]of Object.entries(localState.artifactNames))interfaces.set(localState[name].toLowerCase(),new Interface(bundle[artifact].abi));
 const iface=new Interface(bundle.StrategyManager.abi),registration={adapter:localState.nativeAdapter,inputAsset:ZeroAddress,depositCap:1000000000000000n,maxAllocationBps:5000n,asynchronous:true,active:true};
 const candidate={hash:"0x"+"a".repeat(64),from:ORIGINAL.actor,nonce:23,to:S2.manager,data:iface.encodeFunctionData("registerStrategy",[S2.nativeId,registration]),value:0n,gasLimit:182778n,gasPrice:8000000014n,chainId:16602n,type:2,maxFeePerGas:8000000014n,maxPriorityFeePerGas:8000000014n,accessList:[]};
 const adoptedReceipt={hash:candidate.hash,status:1,blockNumber:S2.block+1,blockHash:"0x"+"b".repeat(64),gasUsed:150000n,gasPrice:8000000014n,contractAddress:null};
 blocks.set(S2.block+1,{number:S2.block+1,hash:adoptedReceipt.blockHash,timestamp:now});
 transactions.set(candidate.hash,candidate);receipts.set(candidate.hash,adoptedReceipt);
 const f={original,stage1,review,bundle,transactions,receipts,blocks,codes:new Map(codes),candidate,adoptedReceipt,registration,mode,pending:mode===S2.adopt?24:23,mined:mode===S2.adopt?24:23,balance:BigInt(S2.balance)-(mode===S2.adopt?adoptedReceipt.gasUsed*adoptedReceipt.gasPrice:0n),count:mode===S2.adopt?1n:0n,candidates:mode===S2.adopt?[candidate]:[],callOverride:null,submissions:0,historicalReads:0};
 f.provider={
  send:async(method,args)=>{if(method==="eth_chainId")return "0x40da";if(method==="eth_getBlockByNumber"){const n=Number(BigInt(args[0])),b=f.blocks.get(n);return b?{...b,number:"0x"+n.toString(16),transactions:n===S2.block+1?f.candidates.map(t=>({...t,nonce:"0x"+t.nonce.toString(16)})):[]}:null;}f.submissions++;throw Error("forbidden RPC");},
  getTransaction:async h=>structuredClone(f.transactions.get(h)),getTransactionReceipt:async h=>structuredClone(f.receipts.get(h)),
  getBlock:async n=>n==="latest"?{number:S2.block+1,hash:adoptedReceipt.blockHash,timestamp:now,baseFeePerGas:7n}:structuredClone(f.blocks.get(n)),
  getCode:async address=>f.codes.get(address.toLowerCase())||"0x",
  getBalance:async(_,tag)=>{if(tag!=null&&tag!=="latest"){f.historicalReads++;throw Error("missing trie node");}return f.balance;},
  getTransactionCount:async(_,tag)=>tag==="pending"?f.pending:f.mined,
  getFeeData:async()=>({gasPrice:4000000007n}),estimateGas:async()=>152315n,
  call:async tx=>{
   const target=tx.to.toLowerCase(),intf=interfaces.get(target),parsed=intf.parseTransaction({data:tx.data});
   if(f.callOverride){const result=f.callOverride(target,parsed);if(result!==undefined)return intf.encodeFunctionResult(parsed.name,[result]);}
   if(target===S2.manager.toLowerCase()){
    if(parsed.name==="strategyCount")return intf.encodeFunctionResult(parsed.name,[f.count]);
    if(parsed.name==="isStrategyActive")return intf.encodeFunctionResult(parsed.name,[parsed.args[0]===S2.nativeId&&f.count>0n?f.registration.active:false]);
    if(parsed.name==="strategyIdAt")return intf.encodeFunctionResult(parsed.name,[S2.nativeId]);
    if(parsed.name==="getStrategy")return intf.encodeFunctionResult(parsed.name,[f.registration]);
   }
   return hre.ethers.provider.call(tx);
  }
 };
 const source="c".repeat(40),tooling="d".repeat(64),state={source,tooling,clean:true,lineage:true,parent:S2.parent,branch:S2.branch};
 f.integrity={state,bundle,artifactHash:ORIGINAL.artifacts,planHash:ORIGINAL.plan};f.recheckSource=()=>state;f.readEvidence=()=>({original:structuredClone(f.original),stage1:structuredClone(f.stage1)});
 f.authorization={mode:"REVIEW_ONLY","expected-chain":"16602","expected-deployer":ORIGINAL.actor,"expected-plan":ORIGINAL.plan,"expected-artifacts":ORIGINAL.artifacts,"expected-source":source,"expected-tooling":tooling,"expected-nonce":String(f.pending),"max-fee-quote-wei":"4000000007","review-expires-at":String(now+600)};
 return f;
}
function temp(f){const dir=fs.mkdtempSync(path.join(os.tmpdir(),"galileo-stage2-")),originalFile=path.join(dir,"original.json"),stage1File=path.join(dir,"stage1.json"),target=path.join(dir,"stage2.json");fs.writeFileSync(originalFile,originalBytes());fs.writeFileSync(stage1File,stage1Bytes());return {dir,originalFile,stage1File,target,protectedFiles:[originalFile,stage1File],provider:f.provider,integrity:f.integrity,readEvidence:()=>readPredecessors({originalFile,stage1File}),beforePersist(){}};}
async function restoreLocal(){await hre.network.provider.send("evm_revert",[localSnapshot]);localSnapshot=await hre.network.provider.send("evm_snapshot");return {state:structuredClone(localState),journal:structuredClone(localPrefix),bundle};}
module.exports={setup,fixture,temp,restoreLocal,originalBytes,stage1Bytes};
