"use strict";
const {Wallet}=require("ethers");
const {assertExactApproval,REVIEWED_PLAN}=require("./release-policy");
const FINAL_BARRIER="STOP: public transaction submission requires separate user broadcast approval";
// Kept for review-only callers; never grants an execution permission.
function finalUserApprovalBarrier(readiness){const e=new Error(FINAL_BARRIER);e.code="SEPARATE_USER_APPROVAL_REQUIRED";e.readiness={...readiness,signerAccessed:false,transactionsSubmitted:0};throw e;}
const permissions=new WeakMap(),credentialPermissions=new WeakMap();
function loadPrivateKeySigner(env,provider,access,makeWallet=(key,p)=>new Wallet(key,p)) {
  const authorizeKey=credentialPermissions.get(access);
  if(!authorizeKey)throw Error("STOP: credential access requires completed readiness/approval");
  authorizeKey();
  // This is the sole credential getter. Production calls it only after all gates.
  let key;
  try {
    key=env.GALILEO_PRIVATE_KEY;
    if(typeof key!=="string"||!/^0x[0-9a-fA-F]{64}$/.test(key))throw Error();
    return makeWallet(key,provider);
  }catch{throw Error("STOP: signing credential missing or invalid");}
  finally{key=undefined;}
}
async function futureSignerBoundary(readiness,loader,authorization,env,recheckSource) {
  if(!authorization)finalUserApprovalBarrier(readiness);
  if(readiness.status!=="PRE_SIGNING_CHECKS_PASSED"||readiness.chainId!==16602||readiness.planHash!==REVIEWED_PLAN||readiness.source!==authorization["approved-source"])throw Error("STOP: completed exact-source readiness required");
  const assertCurrent=()=>{
    assertExactApproval(authorization,env,recheckSource());
    if(BigInt(authorization["review-expires-at"])<=BigInt(Math.floor(Date.now()/1000))+5n)throw Error("STOP: approval review expired");
  };
  assertCurrent();
  let signer;
  const access=Object.freeze({});credentialPermissions.set(access,assertCurrent);
  try{signer=await loader(access);if((await signer.getAddress()).toLowerCase()!==readiness.deployer.toLowerCase())throw Error("mismatch");}
  catch{throw Error("STOP: signing credential unavailable/invalid or signer/deployer mismatch");}
  finally{credentialPermissions.delete(access);}
  assertCurrent();
  const permission=Object.freeze({source:authorization["approved-source"],deployer:readiness.deployer});
  permissions.set(permission,{assertCurrent,policy:Object.freeze({expectedNonce:Number(authorization["expected-nonce"]),maxFeeQuoteWei:authorization["max-fee-quote-wei"],feeCeilingWei:readiness.feeCeilingWei})});
  return {signer,permission};
}
function assertPermission(permission){const entry=permissions.get(permission);if(!entry)throw Error("STOP: missing exact-commit execution permission");entry.assertCurrent();}
function permissionPolicy(permission){assertPermission(permission);return permissions.get(permission).policy;}
module.exports={FINAL_BARRIER,finalUserApprovalBarrier,futureSignerBoundary,loadPrivateKeySigner,assertPermission,permissionPolicy};
