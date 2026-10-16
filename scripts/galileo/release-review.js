"use strict";
const {ContractFactory}=require("ethers");
const {authorize,authorizeReview,assertExactApproval,REVIEWED_PLAN}=require("./release-policy");
const {identity,sourceState}=require("./release-integrity");
const {controlledPlan,reviewed,ceilBps,stop}=require("./controlled-plan");
const {hash}=require("./plan");
const {context,feeQuote,remainingEnvelope,budgetGuard,guardTransaction,validateResume,runGalileo}=require("./controlled-executor");
const {futureSignerBoundary,loadPrivateKeySigner}=require("./release-boundary");
const {releaseStore}=require("./release-journal");
function matchIdentity(expected,actual) {
  if(!actual.state.clean || !actual.state.lineage || actual.state.branch !== "feature/galileo-deployment-tooling")stop("source state must be clean and on approved tooling lineage/branch");
  if(expected.mode==="BROADCAST"&&actual.state.source!==expected["approved-source"])stop("actual HEAD differs from exact user-approved source");
  if(actual.state.source !== expected["expected-source"] || actual.state.tooling !== expected["expected-tooling"])stop("source/tooling fingerprint mismatch");
  if(actual.planHash !== REVIEWED_PLAN || actual.artifactHash !== expected["expected-artifacts"])stop("plan/artifact fingerprint mismatch");
}
// Pure dependency-injected review kernel; no signer interface and no submission.
// The public entry below always binds real repository integrity, never caller state.
async function readinessChecks({authorization,provider,integrity,recheckSource,journal=null}) {
  matchIdentity(authorization,integrity);
  const review=controlledPlan();
  if(review.fingerprint !== authorization["expected-plan"] || hash(review.config)!==hash(reviewed))stop("exact configuration drift");
  if(review.plan.steps.find(s=>s.name === "register4").args[1].active || review.transactionSteps.length !== 33 || review.transactionSteps.filter(s=>s.method === "executeAllocation").length !== 4)stop("Ascend activation/graph drift");
  const actor=review.config.deployer;
  if(journal)await validateResume({provider,bundle:integrity.bundle,review,sourceCommit:integrity.state.source,journal,actor,expectedChain:16602,mode:"GALILEO"});
  const offset=journal?journal.receipts.length:0;
  const c=await context(provider,16602,authorization["expected-deployer"],actor);
  const minedNonce=await provider.getTransactionCount(actor,"latest");
  if(c.nonce !== Number(authorization["expected-nonce"]) || minedNonce !== c.nonce)stop("pending/mined nonce mismatch");
  const now=Math.floor(Date.now()/1000),expires=BigInt(authorization["review-expires-at"]);
  if(!c.block?.hash || Math.abs(now-c.block.timestamp)>180)stop("stale network block");
  if(expires<=BigInt(c.block.timestamp)+30n || expires>BigInt(c.block.timestamp)+900n)stop("stale/excessive review deadline");
  const quote=await feeQuote(provider);
  if(quote>BigInt(authorization["max-fee-quote-wei"]))stop("fee spike above externally reviewed quote limit");
  const ceiling=journal?BigInt(journal.feeCeilingWei):ceilBps(quote,review.config.feeMultiplierBps),reserve=journal?BigInt(journal.reserveWei):ceilBps(c.balance,review.config.reserveBps);
  if(offset<33&&ceilBps(quote,review.config.feeMultiplierBps)>ceiling)stop("fee spike above original execution ceiling");
  const envelope=remainingEnvelope(review.transactionSteps,offset,review.config,ceiling),maximum=ceilBps(envelope,12000);
  if(journal&&BigInt(journal.cumulativeSpendWei)+maximum>BigInt(journal.maxProjectedSpendWei))stop("resume remaining envelope exceeds original cumulative ceiling");
  budgetGuard({balance:c.balance,initialBalance:journal?BigInt(journal.initialBalanceWei):c.balance,reserve,spent:journal?BigInt(journal.cumulativeSpendWei):0n,remaining:maximum});
  const firstGuardJournal={initialBalanceWei:c.balance.toString(),reserveWei:reserve.toString(),feeCeilingWei:ceiling.toString(),cumulativeSpendWei:"0",maxProjectedSpendWei:maximum.toString()};
  let estimate={estimate:0n};
  if(offset===0){
  const first=review.transactionSteps[0];
  const tx=await new ContractFactory(integrity.bundle.StrategyManager.abi,integrity.bundle.StrategyManager.bytecode).getDeployTransaction(actor);
  estimate=await guardTransaction({provider,actor,expectedChain:16602,expectedActor:actor,nonce:c.nonce,request:{...tx,from:actor,value:0n,nonce:c.nonce,deadline:expires},step:first,steps:review.transactionSteps,index:0,config:review.config,journal:firstGuardJournal});
  }
  // Dependent resume steps are estimated by the same engine against confirmed state.
  // Repeat volatile checks and source integrity immediately before credential access.
  const fresh=await context(provider,16602,actor,actor),freshQuote=await feeQuote(provider);
  if(fresh.balance!==c.balance)stop("wallet balance changed during review");
  if(fresh.nonce !== c.nonce || await provider.getTransactionCount(actor,"latest")!==c.nonce)stop("nonce changed during review");
  if(freshQuote>BigInt(authorization["max-fee-quote-wei"]) || (offset<33&&ceilBps(freshQuote,review.config.feeMultiplierBps)>ceiling))stop("fee spike during review");
  if(expires<=BigInt(fresh.block.timestamp)+30n)stop("stale review deadline");
  budgetGuard({balance:fresh.balance,initialBalance:journal?BigInt(journal.initialBalanceWei):c.balance,reserve,spent:journal?BigInt(journal.cumulativeSpendWei):0n,remaining:maximum});
  matchIdentity(authorization,{...integrity,state:recheckSource()});
  return {status:"PRE_SIGNING_CHECKS_PASSED",chainId:16602,deployer:actor,source:integrity.state.source,tooling:integrity.state.tooling,planHash:review.fingerprint,artifactHash:integrity.artifactHash,block:fresh.block.number,blockHash:fresh.block.hash,blockTimestamp:fresh.block.timestamp,nonce:fresh.nonce,balanceWei:fresh.balance.toString(),feeQuoteWei:freshQuote.toString(),feeCeilingWei:ceiling.toString(),reserveWei:reserve.toString(),initialEnvelopeWei:envelope.toString(),maximumProjectedSpendWei:maximum.toString(),totalRequiredWei:(maximum+reserve).toString(),expectedRemainingWei:(fresh.balance-maximum).toString(),headroomWei:(fresh.balance-maximum-reserve).toString(),managerEstimateGas:offset===0?estimate.estimate.toString():null,completedSteps:offset,remainingSteps:33-offset,reviewExpiresAt:expires.toString(),counts:review.plan.counts,publicSubmissionEnabled:false,signerAccessed:false,transactionsSubmitted:0};
}
// Dependency-injected orchestration for tests. Production binds every dependency below;
// callers cannot supply a signer, loader, integrity assertion, store or engine override.
async function executeRelease({authorization,env,provider,integrity,recheckSource,store,loadSigner,runEngine,armProvider}) {
  const journal=store.load();
  const readiness=await readinessChecks({authorization,provider,integrity,recheckSource,journal});
  if(authorization.mode!=="BROADCAST")return {...readiness,status:"READ_ONLY_REVIEW_PASSED"};
  assertExactApproval(authorization,env,recheckSource());
  if(journal?.receipts.length===33)return {status:"ALREADY_COMPLETED",journal,transactionsSubmitted:0};
  const {signer,permission}=await futureSignerBoundary(readiness,loadSigner,authorization,env,recheckSource);
  armProvider(permission);
  try{return await runEngine({provider,signer,bundle:integrity.bundle,sourceCommit:integrity.state.source,store,permission});}
  catch{throw Error("STOP: controlled execution stopped; inspect public receipt journal without resending ambiguous intents");}
}
function publicExecution(options={}) {
  if(!options||Object.keys(options).some(k=>!["args","env","provider"].includes(k)))stop("unsupported release option/configuration drift");
  const reviewOnly=Array.isArray(options.args)&&options.args.includes("--review-only");
  const authorization=reviewOnly?authorizeReview(options.args):authorize(options.args,options.env);
  const integrity=identity();matchIdentity(authorization,integrity);
  if(!reviewOnly){const {ExecutionProvider}=require("./execution-provider");if(!(options.provider instanceof ExecutionProvider))stop("controlled public transport required");}
  const store=releaseStore(authorization,reviewOnly);
  return executeRelease({authorization,env:options.env,provider:options.provider,integrity,recheckSource:sourceState,store,
    loadSigner:access=>loadPrivateKeySigner(options.env,options.provider,access),runEngine:runGalileo,
    armProvider:permission=>options.provider.enableSubmission(permission)}).finally(()=>store.close());
}
module.exports={publicExecution,readinessChecks,matchIdentity,executeRelease};
