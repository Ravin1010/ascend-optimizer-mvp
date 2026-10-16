"use strict";
const fs=require("node:fs"),path=require("node:path");
const {ORIGINAL}=require("./recovery-policy");
const {readOriginal,noSymlink,validateRecoveryPrefix}=require("./recovery-validator");
const {evidenceStore}=require("./evidence-store");
const {executionFingerprint}=require("./controlled-executor");
const {controlledPlan,stop}=require("./controlled-plan");
const {hash}=require("./plan");
const ROOT=path.resolve(__dirname,"../..");
function assertNewTarget(originalFile,target) {
  if(path.resolve(originalFile)===path.resolve(target))stop("recovery cannot overwrite original journal");
  for(const p of [target,target+".lock",target+".tmp"]){noSymlink(p);if(fs.existsSync(p))stop("unexpected recovery journal/lock/temporary state");}
}
function recoveryJournal(original,validated,integrity) {
  return {
    ...structuredClone(original),version:"GALILEO_RECOVERY_V1",sourceCommit:integrity.state.source,
    toolingHash:executionFingerprint(),failure:undefined,
    originalJournalSha256:ORIGINAL.sha256,originalSourceCommit:original.sourceCommit,
    originalExecutionToolingHash:original.toolingHash,originalPlanHash:original.planHash,
    originalArtifactHash:original.artifactHash,originalFailureMarker:structuredClone(original.failure),
    recoveredPrefixLength:3,recoverySourceCommit:integrity.state.source,
    recoveryToolingFingerprint:integrity.state.tooling,currentValidatedNonce:validated.nonce,
    currentValidatedBalanceWei:validated.balance.toString(),validationMethod:validated.validationMethod,pendingIntent:null
  };
}
// No read-only mode writes. Production passes only the fixed isolated paths;
// explicit paths support temporary test fixtures, never CLI path overrides.
async function createRecoveryStore({originalFile=path.join(ROOT,ORIGINAL.originalPath),target=path.join(ROOT,ORIGINAL.recoveryPath),integrity,provider,beforePersist=()=>stop("recovery persistence requires execution permission")}) {
  const original=readOriginal(originalFile);assertNewTarget(originalFile,target);
  const validated=await validateRecoveryPrefix({provider,bundle:integrity.bundle,review:controlledPlan(),journal:original});
  const initial=recoveryJournal(original,validated,integrity);
  readOriginal(originalFile);assertNewTarget(originalFile,target);
  // Validation and signer failures leave no target, lock or temporary file.
  let current=structuredClone(initial),store=null,closed=false,persistenceFailed=false;
  const immutable=value=>{
    const {receipts,pendingIntent,cumulativeSpendWei,failure,...provenance}=value;
    return provenance;
  };
  return {
    load:()=>structuredClone(current),
    save(value){
      if(closed||persistenceFailed)stop("recovery store closed or persistence failed; no retry");
      readOriginal(originalFile);
      if(hash(immutable(value))!==hash(immutable(initial))||hash(value.receipts?.slice(0,3))!==hash(initial.receipts))stop("recovery provenance/limits/prefix changed");
      if(!store){
        assertNewTarget(originalFile,target);
        const intent=value.pendingIntent;
        if(!intent||intent.step!=="nativeAdapter"||intent.nonce!==3||!/^[0-9a-f]{64}$/.test(intent.requestHash||"")||Object.keys(intent).sort().join(",")!=="nonce,requestHash,step"||hash({...value,pendingIntent:null})!==hash(initial))stop("first recovery save requires exact step-4 pending intent");
        // Source, approval, expiry and credential absence are checked again after
        // step-4 estimation/guards, before any evidence file can materialize.
        beforePersist();
        readOriginal(originalFile);assertNewTarget(originalFile,target);
        persistenceFailed=true; // Any partial first-write failure is terminal.
        store=evidenceStore(target,false);
        store.save(value);
        persistenceFailed=false;
      }else{
        noSymlink(target);noSymlink(target+".tmp");
        persistenceFailed=true;
        store.save(value);
        persistenceFailed=false;
      }
      current=structuredClone(value);
    },
    close(){if(closed)return;closed=true;if(store)store.close();}
  };
}
module.exports={assertNewTarget,recoveryJournal,createRecoveryStore};
