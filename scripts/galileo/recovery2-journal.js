"use strict";
const fs=require("node:fs"),path=require("node:path");
const {ORIGINAL}=require("./recovery-policy"),{S2}=require("./recovery2-policy");
const {readPredecessors,validateStage2}=require("./recovery2-validator");
const {noSymlink}=require("./recovery-validator");
const {executionFingerprint}=require("./controlled-executor");
const {evidenceStore}=require("./evidence-store");
const {controlledPlan,stop}=require("./controlled-plan"),{hash}=require("./plan");
const ROOT=path.resolve(__dirname,"../..");
function assertStage2Target(target=path.join(ROOT,S2.target),protectedFiles=[path.join(ROOT,ORIGINAL.originalPath),path.join(ROOT,ORIGINAL.recoveryPath)]){
  if(protectedFiles.some(file=>path.resolve(file)===path.resolve(target)))stop("Stage-2 cannot overwrite predecessor evidence");
  for(const file of [target,target+".lock",target+".tmp"]){noSymlink(file);try{fs.lstatSync(file);}catch(e){if(e.code==="ENOENT")continue;throw e;}stop("unexpected Stage-2 target/lock/tmp");}
}
function stage2Journal({evidence,validated,integrity}){
  const prior=evidence.stage1;
  return {...structuredClone(prior),version:"GALILEO_RECOVERY2_V1",sourceCommit:integrity.state.source,toolingHash:executionFingerprint(),failure:undefined,pendingIntent:null,
    originalJournalSha256:ORIGINAL.sha256,stage1RecoveryJournalSha256:S2.stage1Sha,originalSourceCommit:ORIGINAL.source,stage1RecoverySourceCommit:S2.parent,stage1RecoveryToolingFingerprint:S2.stage1Tooling,stage1ExecutionToolingHash:prior.toolingHash,
    stage1FailureMarker:structuredClone(prior.failure),stage1PendingIntent:structuredClone(prior.pendingIntent),ambiguityRequestHash:S2.requestHash,ambiguityCalldataHash:S2.calldataHash,historicalRequest:require("./recovery2-validator").json(validated.request),
    recoveredPrefixLength:23,recovery2SourceCommit:integrity.state.source,recovery2ToolingFingerprint:integrity.state.tooling,currentValidatedBalanceWei:validated.balance.toString(),currentValidatedNonce:validated.nonce,validationMethod:S2.method,entryMode:validated.mode,adoption:null};
}
async function createStage2Store({provider,integrity,readEvidence=readPredecessors,target=path.join(ROOT,S2.target),protectedFiles,beforePersist=()=>stop("Stage-2 persistence requires permission")}){
  const checkTarget=()=>assertStage2Target(target,protectedFiles);
  const evidence=readEvidence();checkTarget();
  const validated=await validateStage2({provider,bundle:integrity.bundle,review:controlledPlan(),evidence});
  readEvidence();checkTarget();const initial=stage2Journal({evidence,validated,integrity});
  let current=structuredClone(initial),writer=null,closed=false,failed=false;
  const immutable=j=>{const {receipts,pendingIntent,cumulativeSpendWei,failure,adoption,...rest}=j;return rest;};
  return {
    load:()=>structuredClone(current),materialized:()=>writer!==null,
    save(value,proof){
      if(closed||failed)stop("Stage-2 store closed/failed; no retry");readEvidence();
      if(hash(immutable(value))!==hash(immutable(initial))||hash(value.receipts?.slice(0,23))!==hash(initial.receipts)||hash(value.receipts?.slice(0,current.receipts.length))!==hash(current.receipts)||value.receipts.length>current.receipts.length+1||BigInt(value.cumulativeSpendWei)>BigInt(ORIGINAL.maxProjectedSpendWei)||BigInt(value.cumulativeSpendWei)<BigInt(current.cumulativeSpendWei))stop("Stage-2 evidence/provenance/envelope drift");
      const adopting=value.adoption===S2.adoption&&value.adoption!==current.adoption;
      if(adopting&&(!proof||proof.mode!==S2.adopt||value.receipts.length!==24||hash(value.receipts[23])!==hash(proof.adoptedRecord)||value.pendingIntent!==null||value.cumulativeSpendWei!==proof.adoptedRecord.cumulativeSpendWei))stop("exact canonical adoption proof required");
      if(current.adoption&&value.adoption!==current.adoption)stop("adoption marker cannot change");
      if(!writer){
        checkTarget();
        const intent=value.pendingIntent;
        const replay=initial.entryMode===S2.replay&&intent&&hash(intent)===hash({step:"register0",nonce:23,requestHash:S2.requestHash})&&hash({...value,pendingIntent:null})===hash(initial);
        const adopted=adopting&&hash({...value,receipts:initial.receipts,cumulativeSpendWei:initial.cumulativeSpendWei,adoption:null})===hash(initial);
        if(!replay&&!adopted)stop("invalid first Stage-2 intent/adoption state");
        beforePersist();readEvidence();checkTarget();failed=true;writer=evidenceStore(target,false);writer.save(value);failed=false;
      }else{noSymlink(target);noSymlink(target+".tmp");failed=true;writer.save(value);failed=false;}
      current=structuredClone(value);
    },
    close(){if(closed)return;closed=true;if(writer)writer.close();}
  };
}
module.exports={assertStage2Target,stage2Journal,createStage2Store};
