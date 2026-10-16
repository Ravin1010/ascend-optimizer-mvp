"use strict";
const path=require("node:path"),{execFileSync}=require("node:child_process");
const {sanitizedChildEnv}=require("./subprocess-env");
const {identity,sourceState}=require("./release-integrity");
const {ORIGINAL,recoveryAuthorization,assertRecoverySource,assertRecoveryApproval}=require("./recovery-policy");
const {readOriginal,validateRecoveryPrefix}=require("./recovery-validator");
const {assertNewTarget,recoveryJournal,createRecoveryStore}=require("./recovery-journal");
const {controlledPlan,ceilBps,stop}=require("./controlled-plan");
const {hash}=require("./plan");
const {feeQuote,remainingEnvelope,budgetGuard,transactionRequest,guardTransaction,engine}=require("./controlled-executor");
const {recoverySignerBoundary,loadPrivateKeySigner,assertPermission}=require("./release-boundary");
const ROOT=path.resolve(__dirname,"../..");
function recoverySourceState() {
  return {...sourceState(),parent:execFileSync("git",["rev-parse","HEAD^"],{cwd:ROOT,env:sanitizedChildEnv(),encoding:"utf8",stdio:["ignore","pipe","pipe"]}).trim()};
}
function matchRecovery(a,integrity) {
  assertRecoverySource(a,integrity.state);
  if(integrity.planHash!==ORIGINAL.plan||integrity.artifactHash!==ORIGINAL.artifacts||a["expected-plan"]!==ORIGINAL.plan||a["expected-artifacts"]!==ORIGINAL.artifacts)stop("recovery frozen plan/artifacts mismatch");
}
async function recoveryReadiness({authorization:a,provider,integrity,original,recheckSource}) {
  matchRecovery(a,integrity);
  const review=controlledPlan();
  const validated=await validateRecoveryPrefix({provider,bundle:integrity.bundle,review,journal:original});
  const block=await provider.getBlock("latest"),expires=BigInt(a["review-expires-at"]),now=Math.floor(Date.now()/1000);
  if(a["expected-nonce"]!=="3"||!block?.hash||Math.abs(now-block.timestamp)>180||expires<=BigInt(now)+30n||expires<=BigInt(block.timestamp)+30n||expires>BigInt(block.timestamp)+900n)stop("stale recovery block/review/nonce");
  const quote=await feeQuote(provider);
  if(quote>BigInt(a["max-fee-quote-wei"])||ceilBps(quote,review.config.feeMultiplierBps)>BigInt(original.feeCeilingWei))stop("recovery fee quote/ceiling exceeded");
  const envelope=remainingEnvelope(review.transactionSteps,3,review.config,BigInt(original.feeCeilingWei)),maximum=ceilBps(envelope,12000);
  if(BigInt(original.cumulativeSpendWei)+maximum>BigInt(original.maxProjectedSpendWei))stop("recovery remaining envelope exceeds original cumulative ceiling");
  budgetGuard({balance:validated.balance,initialBalance:BigInt(original.initialBalanceWei),reserve:BigInt(original.reserveWei),spent:BigInt(original.cumulativeSpendWei),remaining:maximum});
  const step=review.transactionSteps[3],built=await transactionRequest(step,validated.state,integrity.bundle,provider,ORIGINAL.actor,3,review.config,BigInt(block.timestamp+review.config.deadlineSeconds));
  const guarded=await guardTransaction({provider,actor:ORIGINAL.actor,expectedChain:16602,expectedActor:ORIGINAL.actor,nonce:3,request:{...built.tx,deadline:built.deadline},step,steps:review.transactionSteps,index:3,config:review.config,journal:original});
  // Revalidate volatile evidence and all current state before a credential token exists.
  const fresh=await validateRecoveryPrefix({provider,bundle:integrity.bundle,review,journal:original});
  const freshBlock=await provider.getBlock("latest"),freshQuote=await feeQuote(provider);
  if(Math.abs(Math.floor(Date.now()/1000)-freshBlock.timestamp)>180||expires<=BigInt(Math.floor(Date.now()/1000))+30n||expires<=BigInt(freshBlock.timestamp)+30n||freshQuote>BigInt(a["max-fee-quote-wei"])||ceilBps(freshQuote,20000)>BigInt(original.feeCeilingWei))stop("recovery freshness/fee changed during review");
  assertRecoverySource(a,recheckSource());
  return {validated:fresh,readiness:{status:"PRE_SIGNING_CHECKS_PASSED",chainId:16602,deployer:ORIGINAL.actor,source:integrity.state.source,tooling:integrity.state.tooling,planHash:ORIGINAL.plan,artifactHash:ORIGINAL.artifacts,nonce:3,balanceWei:fresh.balance.toString(),feeQuoteWei:freshQuote.toString(),feeCeilingWei:original.feeCeilingWei,reserveWei:original.reserveWei,initialEnvelopeWei:original.initialEnvelopeWei,maximumProjectedSpendWei:original.maxProjectedSpendWei,remainingEnvelopeWei:envelope.toString(),remainingMaximumWei:maximum.toString(),nextEstimateGas:guarded.estimate.toString(),reviewExpiresAt:expires.toString(),completedSteps:3,remainingSteps:30,signerAccessed:false,transactionsSubmitted:0,publicSubmissionEnabled:false,validationMethod:ORIGINAL.method}};
}
// Testable orchestration; the public entrypoint binds all production dependencies.
async function executeRecovery({authorization,env,provider,integrity,readOriginalJournal,recheckSource,checkTarget,makeStore,loadSigner,armProvider,runEngine}) {
  const original=readOriginalJournal();checkTarget();
  const {validated,readiness}=await recoveryReadiness({authorization,provider,integrity,original,recheckSource});
  readOriginalJournal();checkTarget();
  if(authorization.mode!=="BROADCAST")return {...readiness,status:"RECOVERY_READ_ONLY_REVIEW_PASSED"};
  const recheck=()=>{readOriginalJournal();return recheckSource();};
  assertRecoveryApproval(authorization,env,recheck());
  const initial=recoveryJournal(original,validated,integrity);
  let permission;
  const store=await makeStore(initial,()=>{
    if(!permission)stop("recovery persistence requires completed signer boundary");
    assertPermission(permission);
  });
  try {
    const grant=await recoverySignerBoundary(readiness,loadSigner,authorization,env,recheck);
    const signer=grant.signer;permission=grant.permission;
    armProvider(permission);
    const beforeStep=async()=>{
      assertPermission(permission);
      const quote=await feeQuote(provider);
      if(quote>BigInt(authorization["max-fee-quote-wei"])||ceilBps(quote,20000)>BigInt(original.feeCeilingWei))stop("recovery execution fee ceiling exceeded");
    };
    const validateExisting=async({journal})=>{
      if(hash(journal)!==hash(initial)||journal.version!=="GALILEO_RECOVERY_V1")stop("recovery starting journal changed");
      readOriginalJournal();
      return (await validateRecoveryPrefix({provider,bundle:integrity.bundle,review:controlledPlan(),journal:original})).state;
    };
    return await runEngine({provider,signer,actor:ORIGINAL.actor,bundle:integrity.bundle,review:controlledPlan(),sourceCommit:integrity.state.source,store,expectedChain:16602,mode:"GALILEO",beforeStep,expectedNonce:3,approvedFeeCeilingWei:original.feeCeilingWei,validateExisting});
  }finally{store.close();}
}
function publicRecovery({args,env,provider,...unsupported}) {
  if(Object.keys(unsupported).length)stop("unsupported recovery options");
  const authorization=recoveryAuthorization(args,env),integrity={...identity(),state:recoverySourceState()};
  matchRecovery(authorization,integrity);
  if(authorization.mode==="BROADCAST"&&!(provider instanceof require("./execution-provider").ExecutionProvider))stop("controlled recovery transport required");
  const originalFile=path.join(ROOT,ORIGINAL.originalPath),target=path.join(ROOT,ORIGINAL.recoveryPath);
  return executeRecovery({authorization,env,provider,integrity,readOriginalJournal:()=>readOriginal(originalFile),recheckSource:recoverySourceState,checkTarget:()=>assertNewTarget(originalFile,target),makeStore:(_initial,beforePersist)=>createRecoveryStore({originalFile,target,integrity,provider,beforePersist}),loadSigner:access=>loadPrivateKeySigner(env,provider,access),armProvider:permission=>provider.enableSubmission(permission),runEngine:engine});
}
module.exports={recoverySourceState,matchRecovery,recoveryReadiness,executeRecovery,publicRecovery};
