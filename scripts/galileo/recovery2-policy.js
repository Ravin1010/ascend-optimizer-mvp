"use strict";
const {ORIGINAL}=require("./recovery-policy");
const {authorize,authorizeReview}=require("./release-policy");
const {stop}=require("./controlled-plan");
const S2=Object.freeze({
  parent:"d76f56dc3049a9ee08b9cfd1c27d18c5ff85fd69",
  stage1Sha:"87fa795e04221724bbb6c8e7495c57f9907c49f580346257f5af29d76596e3fa",
  stage1Tooling:"418fe77269b4a29e63606b2e8c0da07ae71fd8c255f50c0506ce60eb8baf5317",
  stage1Execution:"aaab363729ecc3a61fdc2bac66e6ec7a1bfe331aa8a97045569aef171c987b7d",
  branch:"feature/galileo-recovery2-tooling",target:"galileo-local/final-galileo-recovery2.json",
  balance:"1946071775713125608",spent:"163844224286727392",block:60440605,
  manager:"0x4D7C7286936325eE8b47DF7550Ce8475A7B358E7",
  requestHash:"3706666393264b23ac829814f9f8c1612c5405cfe6b4aa7792c0e3919ca8ca05",
  calldataHash:"0xc565e52633af0f99716ce6b73be4ff7f31ca2ad9fb9755c90909e402189aa9a1",
  nativeId:"0xdd823c4f748efc81bfa8fde64de25e4c4ccb3bafbeeaf78cbfee363137fee226",
  gasLimit:"182778",gasPrice:"8000000014",maxQuote:"4000000007",
  method:"CANONICAL_23_RECEIPTS_EXACT_INTENT_NONCE23_RECOVERY_V1",
  replay:"EXACT_INTENT_REPLAY",adopt:"EXACT_MINED_ADOPTION",adoption:"ADOPTED_EXACT_HISTORICAL_INTENT"
});
function assertStage2Source(a,s){
  if([ORIGINAL.source,S2.parent].includes(a["expected-source"])||!s.clean||!s.lineage||s.branch!==S2.branch||s.parent!==S2.parent||s.source!==a["expected-source"]||s.tooling!==a["expected-tooling"])stop("new exact Stage-2 source/parent/branch/tooling required");
}
function assertStage2Approval(a,env,s){
  if(a.mode!=="BROADCAST"||env.GALILEO_ALLOW_BROADCAST!=="YES"||a["approved-source"]!==a["expected-source"]||env.GALILEO_USER_APPROVED_SOURCE!==a["approved-source"])stop("exact new Stage-2 approval required");
  assertStage2Source(a,s);
}
function stage2Authorization(args,env){
  const a=args.includes("--review-only")?authorizeReview(args):authorize(args,env);
  if(a.resume||[ORIGINAL.source,S2.parent].includes(a["expected-source"])||!["23","24"].includes(a["expected-nonce"])||a["expected-artifacts"]!==ORIGINAL.artifacts||a.journal&&a.journal!==S2.target)stop("unsupported Stage-2 lineage/nonce/journal/resume");
  return a;
}
module.exports={S2,assertStage2Source,assertStage2Approval,stage2Authorization};
