"use strict";
const FINAL_BARRIER="STOP: public transaction submission requires separate user broadcast approval";
function finalUserApprovalBarrier(readiness) {
  const error=new Error(FINAL_BARRIER);
  error.code="SEPARATE_USER_APPROVAL_REQUIRED";
  // Only allowlisted public readiness data is attached; no caller options/env/errors.
  error.readiness=Object.freeze({...readiness,signerAccessed:false,transactionsSubmitted:0});
  throw error;
}
async function futureSignerBoundary(readiness,loader) {
  finalUserApprovalBarrier(readiness);
  // Unreachable in this release. A future reviewed approval mechanism must replace
  // the barrier, not infer consent from CLI flags, funding, tests or acknowledgement.
  // No concrete private-key reader exists. GALILEO_PRIVATE_KEY is reserved in docs.
  const signer=await loader();
  if((await signer.getAddress()).toLowerCase()!==readiness.deployer.toLowerCase())throw Error("STOP: signer/deployer mismatch");
  return signer;
}
module.exports={FINAL_BARRIER,finalUserApprovalBarrier,futureSignerBoundary};
