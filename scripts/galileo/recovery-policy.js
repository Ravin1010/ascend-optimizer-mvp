"use strict";
const {authorize,authorizeReview,REVIEWED_PLAN}=require("./release-policy");
const {stop}=require("./controlled-plan");
const ORIGINAL=Object.freeze({
  sha256:"e9e8a7b7c333e577dad322174662db20f8f94f836b55c731e3e9c5e8b946d111",
  source:"47c1123a84123a969d1ef7b8399c4788db278c2f",
  execution:"461a5101802e8b4299382f80d763f5c76c103d403a03548ed24609157328572e",
  plan:REVIEWED_PLAN,artifacts:"1ff4199614bfd3a665ad99f38c0ed0b8be21c43640f28a81e402f7563ff450d1",
  actor:"0x3e094d9068b48850f09Fc7cc70A7E24E5ed0442a",
  balance:"2077236815942664428",initialBalanceWei:"2109915999999853000",
  reserveWei:"421983199999970600",feeCeilingWei:"8000000014",
  cumulativeSpendWei:"32679184057188572",initialEnvelopeWei:"218459824382287192",
  maxProjectedSpendWei:"262151789258744631",
  originalPath:"galileo-local/final-galileo-receipts.json",
  recoveryPath:"galileo-local/final-galileo-recovery.json",
  branch:"feature/galileo-recovery-tooling",method:"CANONICAL_RECEIPTS_EXACT_CURRENT_BALANCE_NON_ARCHIVE_V1"
});
function assertRecoverySource(a,state) {
  if(a["expected-source"]===ORIGINAL.source)stop("old deployment source cannot authorize recovery");
  if(!state.clean||!state.lineage||state.branch!==ORIGINAL.branch||state.parent!==ORIGINAL.source||state.source!==a["expected-source"]||state.tooling!==a["expected-tooling"])stop("exact recovery source/tooling/parent/branch mismatch");
}
function assertRecoveryApproval(a,env,state) {
  if(a.mode!=="BROADCAST"||env.GALILEO_ALLOW_BROADCAST!=="YES")stop("explicit recovery broadcast required");
  if(a["approved-source"]===ORIGINAL.source||a["approved-source"]!==a["expected-source"]||env.GALILEO_USER_APPROVED_SOURCE!==a["approved-source"])stop("new exact recovery source approval required");
  assertRecoverySource(a,state);
}
function recoveryAuthorization(args,env) {
  const review=args.includes("--review-only");
  const a=review?authorizeReview(args):authorize(args,env);
  if(a.resume||a["expected-source"]===ORIGINAL.source||a["expected-nonce"]!=="3"||a["expected-artifacts"]!==ORIGINAL.artifacts||a.journal&&a.journal!==ORIGINAL.recoveryPath)stop("unsupported recovery lineage/nonce/journal/resume");
  return a;
}
module.exports={ORIGINAL,recoveryAuthorization,assertRecoverySource,assertRecoveryApproval};
