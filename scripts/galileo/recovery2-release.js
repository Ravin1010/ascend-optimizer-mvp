"use strict";
const path=require("node:path");
const {identity}=require("./release-integrity"),{recoverySourceState}=require("./recovery-release");
const {ORIGINAL}=require("./recovery-policy"),{S2,assertStage2Source,assertStage2Approval,stage2Authorization}=require("./recovery2-policy");
const {readPredecessors,validateStage2}=require("./recovery2-validator");
const {createStage2Store,assertStage2Target}=require("./recovery2-journal");
const {exactReplayGuard,resolveStep24,continueStage2}=require("./recovery2-executor");
const {controlledPlan,ceilBps,stop}=require("./controlled-plan");
const {feeQuote,remainingEnvelope,budgetGuard,transactionRequest,guardTransaction}=require("./controlled-executor");
const {stage2SignerBoundary,loadPrivateKeySigner,assertPermission}=require("./release-boundary");
const ROOT=path.resolve(__dirname,"../..");
function matchStage2(a,i){assertStage2Source(a,i.state);if(i.planHash!==ORIGINAL.plan||i.artifactHash!==ORIGINAL.artifacts||a["expected-plan"]!==ORIGINAL.plan||a["expected-artifacts"]!==ORIGINAL.artifacts)stop("Stage-2 frozen fingerprints mismatch");}
async function stage2Readiness({authorization:a,provider,integrity,readEvidence,recheckSource,validate=validateStage2}){
  matchStage2(a,integrity);const evidence=readEvidence(),review=controlledPlan();
  const validated=await validate({provider,bundle:integrity.bundle,review,evidence});
  if(validated.nonce!==Number(a["expected-nonce"])&&!(a["expected-nonce"]==="23"&&validated.mode===S2.adopt))stop("Stage-2 reviewed nonce mismatch");
  const block=await provider.getBlock("latest"),now=Math.floor(Date.now()/1000),expiry=BigInt(a["review-expires-at"]),quote=await feeQuote(provider);
  if(!block?.hash||Math.abs(now-block.timestamp)>180||expiry<=BigInt(now)+30n||expiry<=BigInt(block.timestamp)+30n||expiry>BigInt(block.timestamp)+900n)stop("Stage-2 review freshness/expiry failed");
  if(quote>BigInt(a["max-fee-quote-wei"])||ceilBps(quote,20000)>BigInt(ORIGINAL.feeCeilingWei))stop("Stage-2 reviewed fee ceiling exceeded");
  const offset=validated.mode===S2.adopt?24:23,spent=validated.adoptedRecord?BigInt(validated.adoptedRecord.cumulativeSpendWei):BigInt(S2.spent);
  const envelope=remainingEnvelope(review.transactionSteps,offset,review.config,BigInt(ORIGINAL.feeCeilingWei)),maximum=ceilBps(envelope,12000);
  if(spent+maximum>BigInt(ORIGINAL.maxProjectedSpendWei))stop("Stage-2 remaining cumulative envelope exceeded");
  budgetGuard({balance:validated.balance,initialBalance:BigInt(ORIGINAL.initialBalanceWei),reserve:BigInt(ORIGINAL.reserveWei),spent,remaining:maximum});
  let nextGuard;
  if(validated.mode===S2.replay)nextGuard=await exactReplayGuard({provider,validated,journal:evidence.stage1,bundle:integrity.bundle,review,maxQuote:a["max-fee-quote-wei"]});
  else{
    const step=review.transactionSteps[24],built=await transactionRequest(step,validated.state,integrity.bundle,provider,ORIGINAL.actor,24,review.config,0n);
    nextGuard=await guardTransaction({provider,actor:ORIGINAL.actor,expectedChain:16602,expectedActor:ORIGINAL.actor,nonce:24,request:built.tx,step,steps:review.transactionSteps,index:24,config:review.config,journal:{...evidence.stage1,cumulativeSpendWei:spent.toString()}});
  }
  readEvidence();assertStage2Source(a,recheckSource());
  return {validated,readiness:{status:"PRE_SIGNING_CHECKS_PASSED",chainId:16602,deployer:ORIGINAL.actor,source:integrity.state.source,tooling:integrity.state.tooling,planHash:ORIGINAL.plan,artifactHash:ORIGINAL.artifacts,mode:validated.mode,nonce:validated.nonce,balanceWei:validated.balance.toString(),completedSteps:offset,remainingSteps:33-offset,nextStep:review.transactionSteps[offset].name,nextEstimateGas:nextGuard.estimate.toString(),feeQuoteWei:quote.toString(),feeCeilingWei:ORIGINAL.feeCeilingWei,reserveWei:ORIGINAL.reserveWei,cumulativeSpendWei:spent.toString(),maxProjectedSpendWei:ORIGINAL.maxProjectedSpendWei,remainingEnvelopeWei:envelope.toString(),remainingMaximumWei:maximum.toString(),reviewExpiresAt:expiry.toString(),validationMethod:S2.method,signerAccessed:false,transactionsSubmitted:0,publicSubmissionEnabled:false}};
}
// Dependency-injected test kernel; publicStage2 binds every production dependency.
async function executeStage2({authorization,env,provider,integrity,readEvidence,recheckSource,checkTarget,makeStore,loadSigner,armProvider,validate=validateStage2,resolve=resolveStep24,continueExecution=continueStage2}){
  let phase="VALIDATION",store=null,permission;
  const setPhase=value=>{phase=value;};
  try{
    checkTarget();const checked=await stage2Readiness({authorization,provider,integrity,readEvidence,recheckSource,validate});readEvidence();checkTarget();
    if(authorization.mode!=="BROADCAST")return {...checked.readiness,status:"RECOVERY2_READ_ONLY_REVIEW_PASSED"};
    const source=()=>{readEvidence();return recheckSource();};
    phase="APPROVAL";assertStage2Approval(authorization,env,source());
    const checkPermission=()=>{readEvidence();assertPermission(permission);};
    store=await makeStore(()=>{if(!permission)stop("Stage-2 signer boundary incomplete");checkPermission();});
    if(checked.validated.mode===S2.adopt&&store.load().entryMode!==S2.adopt)stop("reviewed adoption mode changed before signer boundary");
    phase="SIGNER_BOUNDARY";const grant=await stage2SignerBoundary(checked.readiness,loadSigner,authorization,env,source);permission=grant.permission;armProvider(permission);
    const revalidate=async()=>{
      readEvidence();checkPermission();const value=await validate({provider,bundle:integrity.bundle,review:controlledPlan(),evidence:readEvidence()});
      if(checked.validated.mode===S2.adopt&&(value.mode!==S2.adopt||value.adoptedRecord.transactionHash!==checked.validated.adoptedRecord.transactionHash||value.adoptedRecord.blockHash!==checked.validated.adoptedRecord.blockHash))stop("reviewed canonical adoption changed");
      checkPermission();return value;
    };
    await resolve({provider,signer:grant.signer,store,bundle:integrity.bundle,revalidate,checkPermission,maxQuote:authorization["max-fee-quote-wei"],phase:setPhase});
    phase="SHARED_ENGINE";return await continueExecution({provider,signer:grant.signer,store,bundle:integrity.bundle,sourceCommit:integrity.state.source,checkPermission,maxQuote:authorization["max-fee-quote-wei"]});
  }catch{
    if(store?.materialized()){
      const j=store.load();j.failure={step:j.pendingIntent?.step||controlledPlan().transactionSteps[j.receipts.length]?.name||"VERIFY",status:"STOPPED",errorCode:"STAGE2_EXECUTION_FAILED",phase};
      try{store.save(j);}catch{/* Preserve partial durable evidence; never retry submission. */}
    }
    const error=Error(`STOP: Stage-2 ${phase} failed; preserve all evidence; no retry`);error.phase=phase;throw error;
  }finally{store?.close();}
}
function publicStage2({args,env,provider,...unknown}){
  if(Object.keys(unknown).length)stop("unsupported Stage-2 options");const authorization=stage2Authorization(args,env),integrity={...identity(),state:recoverySourceState()};matchStage2(authorization,integrity);
  if(authorization.mode==="BROADCAST"&&!(provider instanceof require("./execution-provider").ExecutionProvider))stop("controlled Stage-2 transport required");
  const target=path.join(ROOT,S2.target);
  return executeStage2({authorization,env,provider,integrity,readEvidence:readPredecessors,recheckSource:recoverySourceState,checkTarget:()=>assertStage2Target(target),makeStore:beforePersist=>createStage2Store({provider,integrity,beforePersist}),loadSigner:access=>loadPrivateKeySigner(env,provider,access),armProvider:permission=>provider.enableSubmission(permission)});
}
module.exports={matchStage2,stage2Readiness,executeStage2,publicStage2};
