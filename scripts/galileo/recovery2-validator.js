"use strict";
const fs=require("node:fs"),path=require("node:path");
const {Contract,getCreateAddress,keccak256,id}=require("ethers");
const {ORIGINAL}=require("./recovery-policy");
const {S2}=require("./recovery2-policy");
const {readOriginal,noSymlink,sha256}=require("./recovery-validator");
const {hash,IDS}=require("./plan");
const {stop}=require("./controlled-plan");
const {transactionRequest}=require("./controlled-executor");
const {runtimeMatches,verifyState}=require("./controlled-state");
const ROOT=path.resolve(__dirname,"../..");
const json=v=>JSON.parse(JSON.stringify(v,(_,x)=>typeof x==="bigint"?x.toString():x));
const same=(a,b)=>String(a??"").toLowerCase()===String(b??"").toLowerCase();
function validateStage1(j,original){
  const expected={version:"GALILEO_RECOVERY_V1",mode:"GALILEO",sourceCommit:S2.parent,recoverySourceCommit:S2.parent,toolingHash:S2.stage1Execution,recoveryToolingFingerprint:S2.stage1Tooling,planHash:ORIGINAL.plan,artifactHash:ORIGINAL.artifacts,actor:ORIGINAL.actor,publicDeployer:ORIGINAL.actor,chainId:16602,targetChainId:16602,startNonce:0,originalJournalSha256:ORIGINAL.sha256,originalSourceCommit:ORIGINAL.source,originalExecutionToolingHash:ORIGINAL.execution,cumulativeSpendWei:S2.spent};
  for(const [k,v]of Object.entries(expected))if(j[k]!==v)stop("Stage-1 provenance mismatch: "+k);
  for(const k of ["initialBalanceWei","reserveWei","feeCeilingWei","initialEnvelopeWei","maxProjectedSpendWei"])if(j[k]!==ORIGINAL[k])stop("Stage-1 envelope mismatch: "+k);
  if(!Array.isArray(j.receipts)||j.receipts.length!==23||new Set(j.receipts.map(r=>r.transactionHash)).size!==23||hash(j.receipts.slice(0,3))!==hash(original.receipts))stop("Stage-1 exact prefix mismatch");
  const names=require("./controlled-plan").controlledPlan().transactionSteps;
  for(let n=0;n<23;n++){const r=j.receipts[n];if(r.number!==n+1||r.step!==names[n].name||r.kind!==names[n].kind||r.nonce!==n||r.status!=="CONFIRMED")stop("Stage-1 receipt order/nonce/status mismatch");}
  const last=j.receipts[22];
  if(last.step!=="ascendAdapter"||last.transactionHash!=="0x348b98fe7e9b0da16eae00239b3656160f11ff7541daf95b121de1849ad7d2f4"||last.blockNumber!==S2.block||last.deployedAddress!=="0x25339Ef4E45D9982B7c51631a5C48542210f90Ea"||last.walletBalanceAfterWei!==S2.balance||last.cumulativeSpendWei!==S2.spent)stop("Stage-1 last confirmation mismatch");
  if(hash(j.pendingIntent)!==hash({step:"register0",nonce:23,requestHash:S2.requestHash})||hash(j.failure)!==hash({step:"register0",status:"STOPPED",errorCode:"EXECUTION_OR_VERIFICATION_FAILED"}))stop("Stage-1 preserved intent/failure mismatch");
  return j;
}
function readPredecessors({originalFile=path.join(ROOT,ORIGINAL.originalPath),stage1File=path.join(ROOT,ORIGINAL.recoveryPath)}={}){
  const original=readOriginal(originalFile);noSymlink(stage1File);const bytes=fs.readFileSync(stage1File);
  if(sha256(bytes)!==S2.stage1Sha)stop("Stage-1 journal SHA-256 mismatch");
  return {original,stage1:validateStage1(JSON.parse(bytes),original)};
}
async function historicalRequest({state,bundle,review,provider}){
  if(review.fingerprint!==ORIGINAL.plan||hash(bundle)!==ORIGINAL.artifacts)stop("Stage-2 frozen plan/artifact mismatch");
  const built=await transactionRequest(review.transactionSteps[23],state,bundle,provider,ORIGINAL.actor,23,review.config,0n);
  const request={...built.tx,chainId:16602,gasLimit:BigInt(S2.gasLimit),gasPrice:BigInt(S2.gasPrice)};
  assertHistoricalRequest(request);return {request,built};
}
function assertHistoricalRequest(r){
  if(Object.keys(r).sort().join(",")!=="chainId,data,from,gasLimit,gasPrice,nonce,to,value"||r.from!==ORIGINAL.actor||r.to!==S2.manager||r.nonce!==23||r.chainId!==16602||r.value!==0n||r.gasLimit!==BigInt(S2.gasLimit)||r.gasPrice!==BigInt(S2.gasPrice)||keccak256(r.data)!==S2.calldataHash||hash(json(r))!==S2.requestHash)stop("exact historical register0 request mismatch");
}
async function verifyRecords({provider,bundle,review,records}){
  const state={owner:ORIGINAL.actor,artifactNames:{},codeHashes:{}},seen=new Set();let spent=0n;
  for(let n=0;n<records.length;n++){
    const r=records[n],step=review.transactionSteps[n],tx=await provider.getTransaction(r.transactionHash),receipt=await provider.getTransactionReceipt(r.transactionHash);
    if(!tx||!receipt||receipt.status!==1||receipt.hash!==r.transactionHash||tx.hash!==r.transactionHash||seen.has(tx.hash)||!same(tx.from,ORIGINAL.actor)||tx.nonce!==n||tx.chainId!==16602n||r.nonce!==n||r.number!==n+1||r.step!==step.name||r.status!=="CONFIRMED"||receipt.blockNumber!==r.blockNumber||receipt.blockHash!==r.blockHash)stop("Stage-2 receipt/nonce/hash mismatch");
    const block=await provider.getBlock(receipt.blockNumber);if(!block||block.hash!==receipt.blockHash)stop("Stage-2 noncanonical receipt");seen.add(tx.hash);
    const built=await transactionRequest(step,state,bundle,provider,ORIGINAL.actor,n,review.config,BigInt(r.deadline||0));
    if(!same(tx.to,built.tx.to)||tx.data!==built.tx.data||tx.value!==built.tx.value||tx.gasLimit!==BigInt(r.gasLimit)||tx.gasPrice!==BigInt(r.effectiveGasPrice)||tx.gasPrice>BigInt(ORIGINAL.feeCeilingWei)||receipt.gasUsed>tx.gasLimit||r.calldata!==tx.data||!same(r.target,tx.to)||hash(r.arguments)!==hash(json(built.args))||hash(r.constructorArguments)!==hash(step.kind==="DEPLOY"?json(built.args):null))stop("Stage-2 transaction body/argument mismatch");
    const cost=receipt.gasUsed*receipt.gasPrice;spent+=cost+tx.value;
    if(r.gasUsed!==receipt.gasUsed.toString()||r.effectiveGasPrice!==receipt.gasPrice.toString()||r.gasCostWei!==cost.toString()||r.valueWei!==tx.value.toString()||r.cumulativeSpendWei!==spent.toString()||r.walletBalanceAfterWei!==(BigInt(ORIGINAL.initialBalanceWei)-spent).toString())stop("Stage-2 receipt accounting mismatch");
    if(step.kind==="DEPLOY"){
      const address=getCreateAddress({from:ORIGINAL.actor,nonce:n});if(!same(receipt.contractAddress,address)||!same(r.deployedAddress,address))stop("Stage-2 CREATE address mismatch");
      const code=await provider.getCode(address);if(!runtimeMatches(code,bundle[step.contract])||keccak256(code)!==r.runtimeCodeHash)stop("Stage-2 runtime mismatch");state[step.name]=address;state.artifactNames[step.name]=step.contract;state.codeHashes[step.name]=keccak256(code);
      if(step.name==="gimoPool"){
        const child=await new Contract(address,bundle.MockGimoStakePool.abi,provider).st0g(),code=await provider.getCode(child);
        if(!runtimeMatches(code,bundle.MockGimoSt0G)||keccak256(code)!==r.childRuntimeCodeHash)stop("Stage-2 child runtime mismatch");state.gimoToken=child;state.artifactNames.gimoToken="MockGimoSt0G";state.codeHashes.gimoToken=keccak256(code);
      }
    }
  }
  return {state,spent};
}
async function exactMinedRecord({provider,request,built,state,bundle,review,transactionHash,adopted=true}){
  const tx=await provider.getTransaction(transactionHash),receipt=await provider.getTransactionReceipt(transactionHash);
  if(!tx||tx.hash!==transactionHash||!same(tx.from,ORIGINAL.actor)||tx.nonce!==23||tx.chainId!==16602n||!same(tx.to,request.to)||tx.data!==request.data||tx.value!==0n||tx.gasLimit!==request.gasLimit||tx.gasPrice!==request.gasPrice)stop("adopted/replayed request differs from historical intent");
  assertHistoricalRequest(request);
  if(tx.type!=null&&![0,2].includes(tx.type)||tx.accessList?.length||tx.maxFeePerGas!=null&&tx.maxFeePerGas!==request.gasPrice||tx.maxPriorityFeePerGas!=null&&tx.maxPriorityFeePerGas!==request.gasPrice)stop("adopted/replayed envelope differs from Wallet gasPrice semantics");
  if(!receipt||receipt.hash!==transactionHash||receipt.status!==1||receipt.gasUsed>request.gasLimit||receipt.gasPrice!==request.gasPrice)stop("adopted/replayed receipt failed/missing");
  const block=await provider.getBlock(receipt.blockNumber);if(!block||block.hash!==receipt.blockHash)stop("adopted/replayed receipt noncanonical");
  const readbacks=await verifyState(provider,bundle,state,review.transactionSteps.slice(0,24).map(s=>s.name),ORIGINAL.actor,review.config);
  const cost=receipt.gasUsed*receipt.gasPrice,spent=BigInt(S2.spent)+cost,balance=await provider.getBalance(ORIGINAL.actor);
  if(balance!==BigInt(S2.balance)-cost||spent>BigInt(ORIGINAL.maxProjectedSpendWei)||balance<BigInt(ORIGINAL.reserveWei))stop("adoption/replay balance/spend mismatch");
  return {number:24,step:"register0",kind:"CONFIGURE",status:"CONFIRMED",error:null,transactionHash,nonce:23,blockNumber:receipt.blockNumber,blockHash:receipt.blockHash,gasLimit:request.gasLimit.toString(),gasUsed:receipt.gasUsed.toString(),effectiveGasPrice:receipt.gasPrice.toString(),gasCostWei:cost.toString(),valueWei:"0",deployedAddress:null,constructorArguments:null,arguments:json(built.args),target:request.to,calldata:request.data,deadline:null,runtimeCodeHash:null,childRuntimeCodeHash:null,events:[],readbacks,cumulativeSpendWei:spent.toString(),walletBalanceAfterWei:balance.toString(),estimatedGas:null,projectedRemainingWei:null,explorerLink:`https://chainscan-galileo.0g.ai/tx/${transactionHash}`,localEvidenceOnly:false,...(adopted?{adoption:S2.adoption}:{})};
}
async function scanNonce23(provider,tip){
  const matches=[];let next=S2.block;
  // Bounded parallel read-only fetches; every block is still examined exactly once.
  async function worker(){while(next<=tip){
    const n=next++,block=await provider.send("eth_getBlockByNumber",["0x"+n.toString(16),true]);
    if(!block||Number(BigInt(block.number))!==n||!block.hash||!Array.isArray(block.transactions)||block.transactions.some(tx=>typeof tx!=="object"))stop("canonical full block unavailable for adoption");
    for(const tx of block.transactions)if(same(tx.from,ORIGINAL.actor)&&Number(BigInt(tx.nonce))===23)matches.push({hash:tx.hash,blockNumber:n,blockHash:block.hash});
  }}
  await Promise.all(Array.from({length:6},worker));
  if(matches.length!==1)stop("adoption requires exactly one mined nonce-23 candidate");return matches[0];
}
async function validateStage2({provider,bundle,review,evidence}){
  const j=validateStage1(evidence.stage1,evidence.original);
  if(review.fingerprint!==ORIGINAL.plan||hash(bundle)!==ORIGINAL.artifacts||Number(BigInt(await provider.send("eth_chainId",[])))!==16602)stop("Stage-2 chain/plan/artifact mismatch");
  const prefix=await verifyRecords({provider,bundle,review,records:j.receipts});if(prefix.spent!==BigInt(S2.spent))stop("Stage-2 prefix spend mismatch");
  const historical=await historicalRequest({state:prefix.state,bundle,review,provider});
  const pending=await provider.getTransactionCount(ORIGINAL.actor,"pending"),mined=await provider.getTransactionCount(ORIGINAL.actor,"latest");let mode,adoptedRecord=null;
  if(pending===23&&mined===23){
    mode=S2.replay;await verifyState(provider,bundle,prefix.state,j.receipts.map(r=>r.step),ORIGINAL.actor,review.config);
    if(await new Contract(prefix.state.manager,bundle.StrategyManager.abi,provider).isStrategyActive(id(IDS[0])))stop("Native already active in replay mode");
    if(await provider.getBalance(ORIGINAL.actor)!==BigInt(S2.balance))stop("Stage-2 replay balance mismatch");
  }else if(pending===24&&mined===24){
    mode=S2.adopt;const latest=await provider.getBlock("latest");const candidate=await scanNonce23(provider,latest.number);
    adoptedRecord=await exactMinedRecord({provider,...historical,state:prefix.state,bundle,review,transactionHash:candidate.hash});
    if(adoptedRecord.blockNumber!==candidate.blockNumber||adoptedRecord.blockHash!==candidate.blockHash)stop("adoption scan/receipt block mismatch");
  }else stop("unsupported Stage-2 pending/mined nonce state");
  const balance=await provider.getBalance(ORIGINAL.actor);
  if(await provider.getTransactionCount(ORIGINAL.actor,"pending")!==pending||await provider.getTransactionCount(ORIGINAL.actor,"latest")!==mined)stop("Stage-2 nonce changed during validation");
  const expected=adoptedRecord?BigInt(adoptedRecord.walletBalanceAfterWei):BigInt(S2.balance);if(balance!==expected)stop("Stage-2 balance changed during validation");
  return {mode,state:prefix.state,balance,nonce:mined,request:historical.request,built:historical.built,adoptedRecord,validationMethod:S2.method};
}
module.exports={json,same,readPredecessors,validateStage1,historicalRequest,assertHistoricalRequest,verifyRecords,exactMinedRecord,scanNonce23,validateStage2};
