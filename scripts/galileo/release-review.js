"use strict";
const {ContractFactory}=require("ethers");
const {authorize,REVIEWED_PLAN}=require("./release-policy");
const {identity,sourceState}=require("./release-integrity");
const {controlledPlan,reviewed,ceilBps,stop}=require("./controlled-plan");
const {hash}=require("./plan");
const {context,feeQuote,remainingEnvelope,budgetGuard,guardTransaction}=require("./controlled-executor");
const {finalUserApprovalBarrier}=require("./release-boundary");
function matchIdentity(expected,actual) {
  if(!actual.state.clean || !actual.state.lineage || actual.state.branch !== "feature/galileo-deployment-tooling")stop("source state must be clean and on approved tooling lineage/branch");
  if(actual.state.source !== expected["expected-source"] || actual.state.tooling !== expected["expected-tooling"])stop("source/tooling fingerprint mismatch");
  if(actual.planHash !== REVIEWED_PLAN || actual.artifactHash !== expected["expected-artifacts"])stop("plan/artifact fingerprint mismatch");
}
// Pure dependency-injected review kernel; no signer interface and no submission.
// The public entry below always binds real repository integrity, never caller state.
async function readinessChecks({authorization,provider,integrity,recheckSource}) {
  matchIdentity(authorization,integrity);
  const review=controlledPlan();
  if(review.fingerprint !== authorization["expected-plan"] || hash(review.config)!==hash(reviewed))stop("exact configuration drift");
  if(review.plan.steps.find(s=>s.name === "register4").args[1].active || review.transactionSteps.length !== 33 || review.transactionSteps.filter(s=>s.method === "executeAllocation").length !== 4)stop("Ascend activation/graph drift");
  const actor=review.config.deployer;
  const c=await context(provider,16602,authorization["expected-deployer"],actor);
  const minedNonce=await provider.getTransactionCount(actor,"latest");
  if(c.nonce !== Number(authorization["expected-nonce"]) || minedNonce !== c.nonce)stop("pending/mined nonce mismatch");
  const now=Math.floor(Date.now()/1000),expires=BigInt(authorization["review-expires-at"]);
  if(!c.block?.hash || Math.abs(now-c.block.timestamp)>180)stop("stale network block");
  if(expires<=BigInt(c.block.timestamp)+30n || expires>BigInt(c.block.timestamp)+900n)stop("stale/excessive review deadline");
  const quote=await feeQuote(provider);
  if(quote>BigInt(authorization["max-fee-quote-wei"]))stop("fee spike above externally reviewed quote limit");
  const ceiling=ceilBps(quote,review.config.feeMultiplierBps),reserve=ceilBps(c.balance,review.config.reserveBps);
  const envelope=remainingEnvelope(review.transactionSteps,0,review.config,ceiling),maximum=ceilBps(envelope,12000);
  budgetGuard({balance:c.balance,initialBalance:c.balance,reserve,spent:0n,remaining:maximum});
  const journal={initialBalanceWei:c.balance.toString(),reserveWei:reserve.toString(),feeCeilingWei:ceiling.toString(),cumulativeSpendWei:"0",maxProjectedSpendWei:maximum.toString()};
  const first=review.transactionSteps[0];
  const tx=await new ContractFactory(integrity.bundle.StrategyManager.abi,integrity.bundle.StrategyManager.bytecode).getDeployTransaction(actor);
  const estimate=await guardTransaction({provider,actor,expectedChain:16602,expectedActor:actor,nonce:c.nonce,request:{...tx,from:actor,value:0n,nonce:c.nonce,deadline:expires},step:first,steps:review.transactionSteps,index:0,config:review.config,journal});
  // Repeat volatile checks and source integrity immediately before the final barrier.
  const fresh=await context(provider,16602,actor,actor),freshQuote=await feeQuote(provider);
  if(fresh.balance!==c.balance)stop("wallet balance changed during review");
  if(fresh.nonce !== c.nonce || await provider.getTransactionCount(actor,"latest")!==c.nonce)stop("nonce changed during review");
  if(freshQuote>BigInt(authorization["max-fee-quote-wei"]) || ceilBps(freshQuote,review.config.feeMultiplierBps)>ceiling)stop("fee spike during review");
  if(expires<=BigInt(fresh.block.timestamp)+30n)stop("stale review deadline");
  budgetGuard({balance:fresh.balance,initialBalance:c.balance,reserve,spent:0n,remaining:maximum});
  matchIdentity(authorization,{...integrity,state:recheckSource()});
  return {status:"PRE_SIGNING_CHECKS_PASSED",chainId:16602,deployer:actor,source:integrity.state.source,tooling:integrity.state.tooling,planHash:review.fingerprint,artifactHash:integrity.artifactHash,block:fresh.block.number,blockHash:fresh.block.hash,blockTimestamp:fresh.block.timestamp,nonce:fresh.nonce,balanceWei:fresh.balance.toString(),feeQuoteWei:freshQuote.toString(),feeCeilingWei:ceiling.toString(),reserveWei:reserve.toString(),initialEnvelopeWei:envelope.toString(),maximumProjectedSpendWei:maximum.toString(),totalRequiredWei:(maximum+reserve).toString(),expectedRemainingWei:(fresh.balance-maximum).toString(),headroomWei:(fresh.balance-maximum-reserve).toString(),managerEstimateGas:estimate.estimate.toString(),reviewExpiresAt:expires.toString(),counts:review.plan.counts,publicSubmissionEnabled:false,signerAccessed:false,transactionsSubmitted:0};
}
function publicExecution(options={}) {
  // Validate external intent before touching a provider, signer-like property or key.
  if(!options || Object.keys(options).some(k=>!["args","env","provider"].includes(k)))stop("unsupported release option/configuration drift");
  const authorization=authorize(options.args,options.env);
  const integrity=identity();
  matchIdentity(authorization,integrity);
  return readinessChecks({authorization,provider:options.provider,integrity,recheckSource:sourceState}).then(finalUserApprovalBarrier);
}
module.exports={publicExecution,readinessChecks,matchIdentity};
