"use strict";
const {ORIGINAL}=require("./recovery-policy"),{S2}=require("./recovery2-policy");
const {controlledPlan,ceilBps,stop}=require("./controlled-plan");
const {hash}=require("./plan");
const {json,assertHistoricalRequest,exactMinedRecord,verifyRecords}=require("./recovery2-validator");
const {feeQuote,guardTransaction,remainingEnvelope,budgetGuard,engine}=require("./controlled-executor");
const {verifyState}=require("./controlled-state");
async function exactReplayGuard({provider,validated,journal,bundle,review,maxQuote}){
  assertHistoricalRequest(validated.request);
  const q=await feeQuote(provider),block=await provider.getBlock("latest");
  if(q>BigInt(S2.maxQuote)||q>BigInt(maxQuote)||BigInt(S2.gasPrice)>BigInt(journal.feeCeilingWei)||block.baseFeePerGas!=null&&block.baseFeePerGas>BigInt(S2.gasPrice))stop("exact replay fee conditions unsafe");
  const step=review.transactionSteps[23],g=await guardTransaction({provider,actor:ORIGINAL.actor,expectedChain:16602,expectedActor:ORIGINAL.actor,nonce:23,request:validated.built.tx,step,steps:review.transactionSteps,index:23,config:review.config,journal});
  if(g.estimate>BigInt(S2.gasLimit)||g.gasLimit>BigInt(S2.gasLimit))stop("fresh gas estimate/margin exceeds historical limit");
  const remaining=BigInt(S2.gasLimit)*BigInt(S2.gasPrice)+remainingEnvelope(review.transactionSteps,24,review.config,BigInt(journal.feeCeilingWei));
  if(BigInt(journal.cumulativeSpendWei)+remaining>BigInt(journal.maxProjectedSpendWei))stop("exact replay cumulative envelope exceeded");
  budgetGuard({balance:validated.balance,initialBalance:BigInt(journal.initialBalanceWei),reserve:BigInt(journal.reserveWei),spent:BigInt(journal.cumulativeSpendWei),remaining});
  return {...g,gasLimit:BigInt(S2.gasLimit),gasPrice:BigInt(S2.gasPrice),projectedRemainingWei:remaining};
}
// One exact ambiguous transaction, never a generic replacement/send loop.
// Production binds revalidate to the pinned Stage-2 validator and permissions.
async function resolveStep24({provider,signer,store,bundle,review=controlledPlan(),revalidate,checkPermission,maxQuote,phase=()=>{}}){
  const adopt=validated=>{
    const j=store.load();
    if(j.receipts.length!==23||!validated.adoptedRecord||validated.mode!==S2.adopt)stop("invalid adoption handoff");
    j.receipts.push(structuredClone(validated.adoptedRecord));j.cumulativeSpendWei=validated.adoptedRecord.cumulativeSpendWei;j.pendingIntent=null;j.adoption=S2.adoption;
    phase("PENDING_INTENT_PERSIST");checkPermission();store.save(j,validated);return {journal:store.load(),state:validated.state,resolution:S2.adoption};
  };
  phase("AMBIGUITY_RECHECK");let v=await revalidate();checkPermission();
  if(v.mode===S2.adopt)return adopt(v);
  phase("ESTIMATE");let guarded=await exactReplayGuard({provider,validated:v,journal:store.load(),bundle,review,maxQuote});
  phase("AMBIGUITY_RECHECK");v=await revalidate();checkPermission();if(v.mode===S2.adopt)return adopt(v);
  // Revalidate the exact request and limits against the last current-state view.
  phase("FEE_GUARD");guarded=await exactReplayGuard({provider,validated:v,journal:store.load(),bundle,review,maxQuote});
  phase("AMBIGUITY_RECHECK");v=await revalidate();checkPermission();if(v.mode===S2.adopt)return adopt(v);
  const j=store.load();j.pendingIntent={step:"register0",nonce:23,requestHash:S2.requestHash};
  phase("PENDING_INTENT_PERSIST");checkPermission();store.save(j);
  phase("PRE_SIGN_PERMISSION");v=await revalidate();checkPermission();if(v.mode===S2.adopt)return adopt(v);
  guarded=await exactReplayGuard({provider,validated:v,journal:store.load(),bundle,review,maxQuote});
  // Full evidence/state validation is the final asynchronous operation before
  // permission recheck and signing; detect adoption or drift during estimation.
  phase("AMBIGUITY_RECHECK");v=await revalidate();checkPermission();if(v.mode===S2.adopt)return adopt(v);
  assertHistoricalRequest(v.request);phase("PRE_SIGN_PERMISSION");checkPermission();
  phase("SUBMISSION");const tx=await signer.sendTransaction(v.request);
  const sent=store.load();sent.pendingIntent.transactionHash=tx.hash;store.save(sent);
  phase("RECEIPT");const receipt=await tx.wait(1);if(!receipt||receipt.status!==1)stop("exact replay missing/failed receipt");
  phase("POST_RECEIPT_STATE");const record=await exactMinedRecord({provider,request:v.request,built:v.built,state:v.state,bundle,review,transactionHash:tx.hash,adopted:false});
  if(receipt.blockHash!==record.blockHash||receipt.blockNumber!==record.blockNumber)stop("exact replay receipt changed");
  record.estimatedGas=guarded.estimate.toString();record.projectedRemainingWei=guarded.projectedRemainingWei.toString();
  const confirmed=store.load();confirmed.receipts.push(record);confirmed.cumulativeSpendWei=record.cumulativeSpendWei;confirmed.pendingIntent=null;store.save(confirmed);
  return {journal:store.load(),state:v.state,resolution:"EXACT_INTENT_REPLAY_CONFIRMED"};
}
async function continueStage2({provider,signer,store,bundle,sourceCommit,checkPermission,maxQuote,runEngine=engine}){
  const review=controlledPlan();
  const beforeStep=async()=>{checkPermission();const q=await feeQuote(provider);if(q>BigInt(maxQuote)||ceilBps(q,20000)>BigInt(ORIGINAL.feeCeilingWei))stop("Stage-2 continuation fee ceiling exceeded");};
  const initial=store.load();if(initial.receipts.length!==24||initial.pendingIntent||initial.failure)stop("Stage-2 shared continuation requires 24 verified receipts");
  const validateExisting=async({journal})=>{
    if(hash(journal)!==hash(initial))stop("Stage-2 shared handoff journal changed");
    const v=await verifyRecords({provider,bundle,review,records:journal.receipts});
    if(await provider.getTransactionCount(ORIGINAL.actor,"pending")!==24||await provider.getTransactionCount(ORIGINAL.actor,"latest")!==24||await provider.getBalance(ORIGINAL.actor)!==BigInt(ORIGINAL.initialBalanceWei)-v.spent)stop("Stage-2 shared handoff state changed");
    await verifyState(provider,bundle,v.state,journal.receipts.map(r=>r.step),ORIGINAL.actor,review.config);return v.state;
  };
  return runEngine({provider,signer,actor:ORIGINAL.actor,bundle,review,sourceCommit,store,expectedChain:16602,mode:"GALILEO",beforeStep,expectedNonce:24,approvedFeeCeilingWei:ORIGINAL.feeCeilingWei,validateExisting});
}
module.exports={exactReplayGuard,resolveStep24,continueStage2};
