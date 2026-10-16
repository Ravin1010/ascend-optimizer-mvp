"use strict";
const {stop,reviewed}=require("./controlled-plan");
const REVIEWED_PLAN="8bf82574f675e6ecff0278ae680f87dcaf9c3fb376714b6caf0c7f08714e333f";
const FIELDS=["expected-chain","expected-deployer","expected-plan","expected-source","expected-tooling","expected-artifacts","expected-nonce","max-fee-quote-wei","review-expires-at"];
function authorize(args,env) {
  if(!Array.isArray(args) || args.filter(a=>a === "--broadcast").length !== 1) stop("explicit --broadcast required");
  // Read exactly this non-secret acknowledgement. Never enumerate/copy env.
  if(env?.GALILEO_ALLOW_BROADCAST !== "YES") stop("external broadcast acknowledgement required");
  const values={};
  for(let i=0;i<args.length;i++) {
    if(args[i] === "--broadcast") continue;
    const key=args[i].slice(2);
    if(!args[i].startsWith("--") || !FIELDS.includes(key) || key in values || !args[i+1] || args[i+1].startsWith("--")) stop("unknown/duplicate/missing release argument");
    values[key]=args[++i];
  }
  if(FIELDS.some(k=>!Object.hasOwn(values,k))) stop("missing expected release identity/fingerprint");
  if(values["expected-chain"] !== "16602") stop("wrong expected chain");
  if(values["expected-deployer"] !== reviewed.deployer) stop("wrong expected deployer");
  if(values["expected-plan"] !== REVIEWED_PLAN) stop("wrong reviewed plan fingerprint");
  if(!/^[0-9a-f]{40}$/.test(values["expected-source"]) || !["expected-tooling","expected-artifacts"].every(k=>/^[0-9a-f]{64}$/.test(values[k]))) stop("invalid source/tooling/artifact fingerprint");
  for(const k of ["expected-nonce","max-fee-quote-wei","review-expires-at"]) if(!/^(0|[1-9][0-9]*)$/.test(values[k])) stop("invalid numeric release limit");
  if(BigInt(values["expected-nonce"]) > BigInt(Number.MAX_SAFE_INTEGER) || BigInt(values["max-fee-quote-wei"]) <= 0n) stop("invalid nonce/fee limit");
  return Object.freeze(values);
}
module.exports={authorize,REVIEWED_PLAN};
