"use strict";
const fs=require("node:fs"),path=require("node:path"),{createHash}=require("node:crypto");
const {getCreateAddress,keccak256}=require("ethers");
const {ORIGINAL}=require("./recovery-policy");
const {hash}=require("./plan");
const {stop}=require("./controlled-plan");
const {transactionRequest}=require("./controlled-executor");
const {runtimeMatches,verifyState}=require("./controlled-state");
const ROOT=path.resolve(__dirname,"../..");
const same=(a,b)=>String(a??"").toLowerCase()===String(b??"").toLowerCase();
const json=v=>JSON.parse(JSON.stringify(v,(_,x)=>typeof x==="bigint"?x.toString():x));
const sha256=bytes=>createHash("sha256").update(bytes).digest("hex");
function noSymlink(file) {
  for(let p=path.resolve(file);;p=path.dirname(p)) {
    if(fs.existsSync(p)&&fs.lstatSync(p).isSymbolicLink())stop("recovery evidence symlink forbidden");
    if(path.dirname(p)===p)break;
  }
}
function validateOriginal(j) {
  const expected={version:"GALILEO_RECEIPTS_V1",mode:"GALILEO",chainId:16602,targetChainId:16602,sourceCommit:ORIGINAL.source,toolingHash:ORIGINAL.execution,planHash:ORIGINAL.plan,artifactHash:ORIGINAL.artifacts,actor:ORIGINAL.actor,publicDeployer:ORIGINAL.actor,startNonce:0,pendingIntent:null};
  for(const [k,v]of Object.entries(expected))if(j[k]!==v)stop(`original journal mismatch: ${k}`);
  for(const k of ["initialBalanceWei","reserveWei","feeCeilingWei","cumulativeSpendWei","initialEnvelopeWei","maxProjectedSpendWei"])if(j[k]!==ORIGINAL[k])stop(`original envelope mismatch: ${k}`);
  if(hash(j.failure)!==hash({step:"nativeAdapter",status:"STOPPED",errorCode:"EXECUTION_OR_VERIFICATION_FAILED"}))stop("original safe-stop failure mismatch");
  if(!Array.isArray(j.receipts)||j.receipts.length!==3)stop("original prefix must contain exactly three receipts");
  const names=["manager","vault","validator"];
  const hashes=["0xd37c40eb878166bdf865bc50da50ab10e4a4bb21fa0de904471ca3d7ce5c8b7d","0x26327250108a8bc1186cb7b86bb2f920c00dedcfb233b24d8eb3a99b3addda67","0x8ed6c19cbc830cb0b80bf427065a16626313270a5a46bad0cf480629f552d481"];
  for(let i=0;i<3;i++){const r=j.receipts[i];if(r.step!==names[i]||r.number!==i+1||r.nonce!==i||r.transactionHash!==hashes[i]||r.status!=="CONFIRMED"||r.kind!=="DEPLOY")stop("original prefix order/nonce/transaction mismatch");}
  return j;
}
function readOriginal(file=path.join(ROOT,ORIGINAL.originalPath)) {
  noSymlink(file);
  const bytes=fs.readFileSync(file);
  if(sha256(bytes)!==ORIGINAL.sha256)stop("original journal SHA-256 mismatch");
  return validateOriginal(JSON.parse(bytes.toString("utf8")));
}
async function validateRecoveryPrefix({provider,bundle,review,journal}) {
  const j=validateOriginal(journal),actor=ORIGINAL.actor;
  if(review.fingerprint!==ORIGINAL.plan||hash(bundle)!==ORIGINAL.artifacts)stop("frozen recovery plan/artifact mismatch");
  if(Number(BigInt(await provider.send("eth_chainId",[])))!==16602)stop("wrong recovery chain");
  const state={owner:actor,artifactNames:{},codeHashes:{}};let spent=0n;
  for(let i=0;i<3;i++) {
    const r=j.receipts[i],step=review.transactionSteps[i];
    const tx=await provider.getTransaction(r.transactionHash),receipt=await provider.getTransactionReceipt(r.transactionHash);
    if(!receipt||receipt.status!==1||receipt.hash!==r.transactionHash||receipt.blockNumber!==r.blockNumber||receipt.blockHash!==r.blockHash)stop("missing/failed/mismatched recovery receipt");
    const block=await provider.getBlock(receipt.blockNumber);
    if(!block||block.hash!==receipt.blockHash)stop("noncanonical recovery receipt");
    const expected=await transactionRequest(step,state,bundle,provider,actor,i,review.config,0n);
    if(!tx||tx.hash!==r.transactionHash||!same(tx.from,actor)||tx.nonce!==i||tx.chainId!==16602n||!same(tx.to,expected.tx.to)||tx.data!==expected.tx.data||tx.value!==expected.tx.value||tx.gasLimit!==BigInt(r.gasLimit)||tx.gasPrice!==BigInt(r.effectiveGasPrice)||tx.gasPrice>BigInt(j.feeCeilingWei))stop("recovery transaction/calldata/value/fee mismatch");
    if(r.calldata!==tx.data||!same(r.target,tx.to)||hash(r.arguments)!==hash(json(expected.args))||hash(r.constructorArguments)!==hash(json(expected.args))||r.valueWei!==tx.value.toString())stop("recovery argument evidence mismatch");
    const address=getCreateAddress({from:actor,nonce:i});
    if(!same(receipt.contractAddress,address)||!same(r.deployedAddress,address))stop("recovery deployment address mismatch");
    const code=await provider.getCode(address);
    if(!runtimeMatches(code,bundle[step.contract])||keccak256(code)!==r.runtimeCodeHash)stop("recovery runtime mismatch");
    state[step.name]=address;state.artifactNames[step.name]=step.contract;state.codeHashes[step.name]=keccak256(code);
    const fee=receipt.gasUsed*receipt.gasPrice;spent+=fee+tx.value;
    if(r.gasUsed!==receipt.gasUsed.toString()||r.effectiveGasPrice!==receipt.gasPrice.toString()||r.gasCostWei!==fee.toString()||r.cumulativeSpendWei!==spent.toString()||r.walletBalanceAfterWei!==(BigInt(j.initialBalanceWei)-spent).toString())stop("recovery receipt/accounting mismatch");
  }
  if(spent.toString()!==j.cumulativeSpendWei)stop("recovery cumulative spend mismatch");
  await verifyState(provider,bundle,state,j.receipts.map(r=>r.step),actor,review.config);
  const balance=await provider.getBalance(actor); // Deliberately current only; no historical trie assumption.
  const pending=await provider.getTransactionCount(actor,"pending"),mined=await provider.getTransactionCount(actor,"latest");
  const next=getCreateAddress({from:actor,nonce:3});
  if(balance.toString()!==ORIGINAL.balance||pending!==3||mined!==3||await provider.getCode(next)!=="0x")stop("recovery current balance/nonce/next-address mismatch");
  return {state,balance,nonce:3,validationMethod:ORIGINAL.method};
}
module.exports={readOriginal,validateOriginal,validateRecoveryPrefix,sha256,noSymlink};
