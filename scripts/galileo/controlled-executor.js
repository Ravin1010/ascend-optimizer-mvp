"use strict";
const { Contract, ContractFactory, Interface, keccak256, getCreateAddress, ZeroAddress } = require("ethers");
const { resolve, hash } = require("./plan");
const { controlledPlan, ceilBps, stop } = require("./controlled-plan");
const { verifyState, runtimeMatches } = require("./controlled-state");
const { broadcastGuard } = require("./preflight");
const fs=require("node:fs");
const path=require("node:path");
const executionFingerprint=()=>hash(["controlled-executor.js","controlled-plan.js","controlled-state.js","plan.js","reviewed-execution.json"].map(f=>fs.readFileSync(path.join(__dirname,f),"utf8")));
const same = (a,b) => String(a || "").toLowerCase() === String(b || "").toLowerCase();
const json = value => JSON.parse(JSON.stringify(value,(_,v)=>typeof v === "bigint" ? v.toString():v));
function publicExecution(options) {
  // Deliberately no provider, signer factory or environment access before this gate.
  broadcastGuard(["--broadcast"], {GALILEO_ALLOW_BROADCAST:"YES"});
  // Unreachable in this release. Any future gate change requires separate review.
  const review=controlledPlan(options.config);
  return engine({...options,review,actor:review.config.deployer,expectedChain:16602,mode:"GALILEO"});
}
async function artifactsFor(hre, plan) {
  const names = [...new Set(plan.steps.filter(s=>s.kind === "DEPLOY").map(s=>s.contract).concat("MockGimoSt0G"))];
  const bundle = {};
  for(const name of names) {
    const a = await hre.artifacts.readArtifact(name);
    if(Object.keys(a.linkReferences).length || Object.keys(a.deployedLinkReferences).length) stop("unexpected linked artifact");
    const info = await hre.artifacts.getBuildInfo(`${a.sourceName}:${name}`);
    if (!info || info.solcVersion !== "0.8.24" || info.input.settings.evmVersion !== "cancun" || info.input.settings.optimizer.runs !== 200) stop("build specification mismatch");
    bundle[name]={abi:a.abi,bytecode:a.bytecode,deployedBytecode:a.deployedBytecode,immutableReferences:info.output.contracts[a.sourceName][name].evm.deployedBytecode.immutableReferences};
  }
  return bundle;
}
async function context(provider, expectedChain, expectedActor, actor) {
  if(!same(actor,expectedActor)) stop("wrong deployer");
  if(Number(BigInt(await provider.send("eth_chainId",[]))) !== expectedChain) stop("wrong chain");
  return {balance:await provider.getBalance(actor),nonce:await provider.getTransactionCount(actor,"pending"),block:await provider.getBlock("latest")};
}
async function feeQuote(provider) {
  const f=await provider.getFeeData();
  if(!f.gasPrice || f.gasPrice <= 0n) stop("fee quote unavailable");
  return f.gasPrice;
}
function remainingEnvelope(steps, offset, config, price) {
  return steps.slice(offset).reduce((n,s)=>n+BigInt(s.value || 0)+ceilBps(s.referenceGas,10000+config.gasMarginBps)*price,0n);
}
function budgetGuard({balance,initialBalance,reserve,spent,remaining}) {
  if(balance < remaining) stop("insufficient balance");
  if(balance-remaining < reserve || initialBalance-spent-remaining < reserve) stop("reserve breach / cumulative spend exceeded");
}
async function guardTransaction({provider,actor,expectedChain,expectedActor,nonce,request,step,steps,index,config,journal}) {
  const c=await context(provider,expectedChain,expectedActor,actor);
  if(c.nonce !== nonce) stop("nonce mismatch");
  if(request.from !== actor || request.nonce !== nonce) stop("transaction identity mismatch");
  const quote=await feeQuote(provider);
  const price=ceilBps(quote,config.feeMultiplierBps);
  if(price > BigInt(journal.feeCeilingWei)) stop("fee spike exceeds reviewed funding envelope");
  let estimate;
  try { const {deadline, ...unsigned}=request; estimate=await provider.estimateGas(unsigned); } catch { stop("gas estimate failure; no local substitute permitted"); }
  const limit=ceilBps(estimate,10000+config.gasMarginBps);
  const remaining=BigInt(request.value || 0)+limit*price+remainingEnvelope(steps,index+1,config,BigInt(journal.feeCeilingWei));
  if(journal.maxProjectedSpendWei && BigInt(journal.cumulativeSpendWei)+remaining > BigInt(journal.maxProjectedSpendWei)) stop("cumulative estimate materially exceeds reviewed funding envelope");
  budgetGuard({balance:c.balance,initialBalance:BigInt(journal.initialBalanceWei),reserve:BigInt(journal.reserveWei),spent:BigInt(journal.cumulativeSpendWei),remaining});
  const now=await provider.getBlock("latest");
  if(request.deadline !== undefined && BigInt(request.deadline) <= BigInt(now.timestamp)+30n) stop("stale deadline");
  return {estimate,gasLimit:limit,gasPrice:price,projectedRemainingWei:remaining,balance:c.balance};
}
function stateFrom(actor) { return {owner:actor,artifactNames:{},codeHashes:{}}; }
async function captureDeployment(provider,bundle,state,name,artifactName,address) {
  const code=await provider.getCode(address);
  if(!runtimeMatches(code,bundle[artifactName])) stop(`incorrect deployed bytecode: ${name}`);
  state[name]=address; state.artifactNames[name]=artifactName; state.codeHashes[name]=keccak256(code);
}
async function childToken(provider,bundle,state) {
  const token=await new Contract(state.gimoPool,bundle.MockGimoStakePool.abi,provider).st0g();
  await captureDeployment(provider,bundle,state,"gimoToken","MockGimoSt0G",token);
}
function eventData(receipt,bundle,state) {
  const out=[];
  for(const log of receipt.logs) {
    const name=Object.keys(state.artifactNames).find(n=>same(state[n],log.address));
    if(!name) continue;
    const decoded=new Interface(bundle[state.artifactNames[name]].abi).parseLog(log);
    if(decoded) out.push({address:log.address,name:decoded.name,signature:decoded.signature,args:json([...decoded.args])});
  }
  return out;
}
async function transactionRequest(step,state,bundle,provider,actor,nonce,config,deadline) {
  state.deadline=deadline;
  const args=resolve(step.args,state);
  let tx;
  if(step.kind === "DEPLOY") tx=await new ContractFactory(bundle[step.contract].abi,bundle[step.contract].bytecode).getDeployTransaction(...args);
  else {
    const target=resolve(step.target,state);
    const name=Object.keys(state.artifactNames).find(n=>same(state[n],target));
    if(!name) stop("unexpected target");
    tx={to:target,data:new Interface(bundle[state.artifactNames[name]].abi).encodeFunctionData(step.method,args)};
  }
  return {args,tx:{from:actor,...tx,value:BigInt(step.value || 0),nonce},deadline:step.method === "executeAllocation" ? deadline : undefined};
}
async function validateResume({provider,bundle,review,sourceCommit,journal,actor,expectedChain,mode="LOCAL_ONLY"}) {
  if(journal.version !== "GALILEO_RECEIPTS_V1" || journal.mode !== mode || journal.chainId !== expectedChain || journal.sourceCommit !== sourceCommit || journal.planHash !== review.fingerprint || journal.toolingHash !== executionFingerprint() || journal.artifactHash !== hash(bundle) || !same(journal.actor,actor)) stop("resume configuration mismatch");
  if(journal.pendingIntent || journal.failure || !Array.isArray(journal.receipts) || journal.receipts.length>33) stop("ambiguous/failed resume; manual review required");
  if(!Number.isSafeInteger(journal.startNonce) || journal.startNonce<0 || BigInt(journal.reserveWei)!==ceilBps(BigInt(journal.initialBalanceWei),review.config.reserveBps)) stop("resume reserve/nonce policy mismatch");
  const envelope=remainingEnvelope(review.transactionSteps,0,review.config,BigInt(journal.feeCeilingWei));
  if(journal.initialEnvelopeWei !== envelope.toString() || journal.maxProjectedSpendWei !== ceilBps(envelope,12000).toString()) stop("resume funding envelope mismatch");
  const state=stateFrom(actor); let spent=0n;
  for(let i=0;i<journal.receipts.length;i++) {
    const r=journal.receipts[i], step=review.transactionSteps[i];
    if(r.step !== step.name || r.number !== i+1 || r.nonce !== journal.startNonce+i || r.status !== "CONFIRMED") stop("duplicate-step / nonce history mismatch");
    const receipt=await provider.getTransactionReceipt(r.transactionHash);
    if(!receipt || receipt.status !== 1 || receipt.blockHash !== r.blockHash || receipt.blockNumber !== r.blockNumber) stop("failed/missing/reorged receipt");
    const tx=await provider.getTransaction(r.transactionHash);
    const expected=await transactionRequest(step,state,bundle,provider,actor,r.nonce,review.config,BigInt(r.deadline || 0));
    if(!tx || !same(tx.from,actor) || tx.nonce !== r.nonce || !same(tx.to,expected.tx.to) || tx.data !== expected.tx.data || tx.value !== expected.tx.value || tx.chainId !== BigInt(expectedChain)) stop("resume transaction/calldata mismatch");
    if(hash(r.arguments)!==hash(json(expected.args)) || r.calldata!==expected.tx.data || !same(r.target,expected.tx.to) || hash(r.constructorArguments)!==hash(step.kind === "DEPLOY"?json(expected.args):null)) stop("resume argument evidence mismatch");
    const canonicalBlock=await provider.getBlock(receipt.blockNumber);
    if(canonicalBlock.hash !== receipt.blockHash) stop("receipt block not canonical");
    if(step.kind === "DEPLOY") {
      const predicted=getCreateAddress({from:actor,nonce:r.nonce});
      if(!same(receipt.contractAddress,predicted) || !same(r.deployedAddress,predicted)) stop("deployment address mismatch");
      await captureDeployment(provider,bundle,state,step.name,step.contract,predicted);
      if(state.codeHashes[step.name] !== r.runtimeCodeHash) stop("runtime hash mismatch");
      if(step.name === "gimoPool") { await childToken(provider,bundle,state); if(state.codeHashes.gimoToken !== r.childRuntimeCodeHash) stop("child runtime mismatch"); }
    }
    if(tx.gasPrice > BigInt(journal.feeCeilingWei)) stop("resume fee exceeds envelope");
    const historicalBalance=await provider.getBalance(actor,receipt.blockNumber);
    if(r.walletBalanceAfterWei !== historicalBalance.toString()) stop("resume balance evidence mismatch");
    const fee=receipt.gasUsed*receipt.gasPrice;
    spent+=fee+tx.value;
    if(r.gasUsed !== receipt.gasUsed.toString() || r.effectiveGasPrice !== receipt.gasPrice.toString() || r.gasCostWei !== fee.toString() || r.cumulativeSpendWei !== spent.toString() || r.valueWei !== tx.value.toString() || r.gasLimit !== tx.gasLimit.toString()) stop("resume evidence cost mismatch");
  }
  if(spent.toString() !== journal.cumulativeSpendWei) stop("resume cumulative spend mismatch");
  const c=await context(provider,expectedChain,actor,actor);
  if(c.nonce !== journal.startNonce+journal.receipts.length) stop("nonce mismatch / unrelated or pending transaction");
  await verifyState(provider,bundle,state,journal.receipts.map(r=>r.step),actor,review.config);
  return state;
}
// Shared state machine. Public entry is unconditionally sealed above.
async function engine({provider,signer,actor,bundle,review,sourceCommit,store,maxSteps=33,expectedChain,mode}) {
  const initial=await context(provider,expectedChain,actor,await signer.getAddress());
  const price=await feeQuote(provider);
  let journal=store.load(); let state;
  if(journal) state=await validateResume({provider,bundle,review,sourceCommit,journal,actor,expectedChain,mode});
  else {
    const reserve=ceilBps(initial.balance,review.config.reserveBps);
    journal={version:"GALILEO_RECEIPTS_V1",mode,chainId:expectedChain,targetChainId:16602,sourceCommit,toolingHash:executionFingerprint(),planHash:review.fingerprint,artifactHash:hash(bundle),actor,publicDeployer:review.config.deployer,startNonce:initial.nonce,initialBalanceWei:initial.balance.toString(),reserveWei:reserve.toString(),feeCeilingWei:ceilBps(price,review.config.feeMultiplierBps).toString(),cumulativeSpendWei:"0",receipts:[],pendingIntent:null,limitations:review.config.limitations};
    budgetGuard({balance:initial.balance,initialBalance:initial.balance,reserve,spent:0n,remaining:ceilBps(remainingEnvelope(review.transactionSteps,0,review.config,BigInt(journal.feeCeilingWei)),12000)});
    journal.initialEnvelopeWei=remainingEnvelope(review.transactionSteps,0,review.config,BigInt(journal.feeCeilingWei)).toString();
    journal.maxProjectedSpendWei=ceilBps(BigInt(journal.initialEnvelopeWei),12000).toString();
    state=stateFrom(actor); store.save(journal);
  }
  try {
    while(journal.receipts.length < Math.min(maxSteps,33)) {
      // Rebuild and hash immediately before every step: injected graph mutations fail closed.
      if(hash({config:review.config,plan:review.plan}) !== review.fingerprint || hash(bundle)!==journal.artifactHash || executionFingerprint()!==journal.toolingHash) stop("configuration/branch/artifact drift");
      const index=journal.receipts.length, step=review.transactionSteps[index], nonce=journal.startNonce+index;
      await verifyState(provider,bundle,state,journal.receipts.map(r=>r.step),actor,review.config);
      const deadline=BigInt((await provider.getBlock("latest")).timestamp+review.config.deadlineSeconds);
      const built=await transactionRequest(step,state,bundle,provider,actor,nonce,review.config,deadline);
      const guarded=await guardTransaction({provider,actor,expectedChain,expectedActor:actor,nonce,request:{...built.tx,deadline:built.deadline},step,steps:review.transactionSteps,index,config:review.config,journal});
      // The deadline is only an ABI argument, never an unknown transaction property.
      const request={...built.tx,chainId:expectedChain,gasLimit:guarded.gasLimit,gasPrice:guarded.gasPrice};
      const requestHash=hash(json(request));
      journal.pendingIntent={step:step.name,nonce,requestHash}; store.save(journal);
      const tx=await signer.sendTransaction(request); // Public entry sealed; tests use only generated local accounts.
      journal.pendingIntent.transactionHash=tx.hash; store.save(journal);
      const receipt=await tx.wait(1);
      if(!receipt || receipt.status !== 1) stop("failed receipt");
      const actual=await provider.getTransaction(tx.hash);
      if(!actual || !same(actual.from,actor) || actual.nonce !== nonce || !same(actual.to,request.to) || actual.data !== request.data || actual.value !== request.value || actual.gasLimit !== request.gasLimit || actual.gasPrice !== request.gasPrice || actual.chainId !== BigInt(expectedChain)) stop("confirmed transaction mismatch");
      if(step.kind === "DEPLOY") {
        const predicted=getCreateAddress({from:actor,nonce});
        if(!same(receipt.contractAddress,predicted)) stop("unexpected deployed address");
        await captureDeployment(provider,bundle,state,step.name,step.contract,predicted);
        if(step.name === "gimoPool") await childToken(provider,bundle,state);
      }
      const readbacks=await verifyState(provider,bundle,state,[...journal.receipts.map(r=>r.step),step.name],actor,review.config);
      const fee=receipt.gasUsed*receipt.gasPrice;
      const cumulative=BigInt(journal.cumulativeSpendWei)+fee+request.value;
      const balance=await provider.getBalance(actor);
      if(balance < BigInt(journal.reserveWei)) stop("reserve breach after receipt");
      const record={number:index+1,step:step.name,kind:step.kind,status:"CONFIRMED",error:null,transactionHash:tx.hash,nonce,blockNumber:receipt.blockNumber,blockHash:receipt.blockHash,gasLimit:request.gasLimit.toString(),gasUsed:receipt.gasUsed.toString(),effectiveGasPrice:receipt.gasPrice.toString(),gasCostWei:fee.toString(),valueWei:request.value.toString(),deployedAddress:receipt.contractAddress,constructorArguments:step.kind === "DEPLOY"?json(built.args):null,arguments:json(built.args),target:request.to || null,calldata:request.data,deadline:built.deadline?.toString() || null,runtimeCodeHash:state.codeHashes[step.name] || null,childRuntimeCodeHash:step.name === "gimoPool"?state.codeHashes.gimoToken:null,events:eventData(receipt,bundle,state),readbacks,cumulativeSpendWei:cumulative.toString(),walletBalanceAfterWei:balance.toString(),estimatedGas:guarded.estimate.toString(),projectedRemainingWei:guarded.projectedRemainingWei.toString(),explorerLink:mode === "LOCAL_ONLY" ? null : `https://chainscan-galileo.0g.ai/tx/${tx.hash}`,localEvidenceOnly:mode === "LOCAL_ONLY"};
      journal.receipts.push(record); journal.cumulativeSpendWei=cumulative.toString(); journal.pendingIntent=null; store.save(journal);
    }
    return {journal,state};
  } catch(error) {
    journal.failure={step:journal.pendingIntent?.step || review.transactionSteps[journal.receipts.length]?.name || "VERIFY",status:"STOPPED",errorCode:"EXECUTION_OR_VERIFICATION_FAILED"};
    store.save(journal); throw error;
  }
}
async function runLocal({hre,config,sourceCommit,store,maxSteps}) {
  // All checks precede signer creation. There is no public-network execution adapter.
  if(hre.network.name !== "hardhat" || Number(BigInt(await hre.ethers.provider.send("eth_chainId",[]))) !== 31337) stop("local executor requires in-process Hardhat 31337");
  await hre.ethers.provider.send("hardhat_metadata",[]);
  const review=controlledPlan(config);
  const bundle=await artifactsFor(hre,review.plan);
  const [signer]=await hre.ethers.getSigners();
  return engine({provider:hre.ethers.provider,signer,actor:await signer.getAddress(),bundle,review,sourceCommit,store,maxSteps,expectedChain:31337,mode:"LOCAL_ONLY"});
}
async function publicPreview(provider,config) {
  const review=controlledPlan(config);
  const c=await context(provider,16602,review.config.deployer,review.config.user);
  const quote=await feeQuote(provider), ceiling=ceilBps(quote,review.config.feeMultiplierBps), reserve=ceilBps(c.balance,review.config.reserveBps);
  const remaining=remainingEnvelope(review.transactionSteps,0,review.config,ceiling);
  budgetGuard({balance:c.balance,initialBalance:c.balance,reserve,spent:0n,remaining:ceilBps(remaining,12000)});
  return json({mode:"PUBLIC_READ_ONLY",broadcastReady:false,transactionsSubmitted:0,block:{number:c.block.number,hash:c.block.hash,timestamp:c.block.timestamp},balanceWei:c.balance,feeQuoteWei:quote,feeCeilingWei:ceiling,reserveWei:reserve,projectedRequirementWei:ceilBps(remaining,12000)+reserve,initialEnvelopeWei:remaining,materialGrowthBps:2000,planHash:review.fingerprint,counts:review.plan.counts});
}
module.exports={runLocal,publicExecution,publicPreview,artifactsFor,context,feeQuote,remainingEnvelope,budgetGuard,guardTransaction,validateResume,transactionRequest};
