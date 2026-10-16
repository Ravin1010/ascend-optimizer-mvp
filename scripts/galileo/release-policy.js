"use strict";
const {stop,reviewed}=require("./controlled-plan");
const REVIEWED_PLAN="8bf82574f675e6ecff0278ae680f87dcaf9c3fb376714b6caf0c7f08714e333f";
const FIELDS=["expected-chain","expected-deployer","expected-plan","expected-source","expected-tooling","expected-artifacts","expected-nonce","max-fee-quote-wei","review-expires-at"];
function parse(args,mode) {
  const flag=mode==="BROADCAST"?"--broadcast":"--review-only";
  if(!Array.isArray(args)||args.filter(a=>a===flag).length!==1)stop("explicit --broadcast or --review-only required");
  const values={mode};
  for(let i=0;i<args.length;i++) {
    if(args[i]===flag)continue;
    if(args[i]==="--resume"){if(values.resume)stop("duplicate resume flag");values.resume=true;continue;}
    const key=args[i].slice(2),allowed=[...FIELDS,"approved-source","journal"];
    if(!args[i].startsWith("--")||!allowed.includes(key)||key in values||!args[i+1]||args[i+1].startsWith("--"))stop("unknown/duplicate/missing release argument");
    values[key]=args[++i];
  }
  if(FIELDS.some(k=>!Object.hasOwn(values,k)))stop("missing expected release identity/fingerprint");
  if(values["expected-chain"]!=="16602")stop("wrong expected chain");
  if(values["expected-deployer"]!==reviewed.deployer)stop("wrong expected deployer");
  if(values["expected-plan"]!==REVIEWED_PLAN)stop("wrong reviewed plan fingerprint");
  if(!/^[0-9a-f]{40}$/.test(values["expected-source"])||!["expected-tooling","expected-artifacts"].every(k=>/^[0-9a-f]{64}$/.test(values[k])))stop("invalid source/tooling/artifact fingerprint");
  for(const k of ["expected-nonce","max-fee-quote-wei","review-expires-at"])if(!/^(0|[1-9][0-9]*)$/.test(values[k]))stop("invalid numeric release limit");
  if(BigInt(values["expected-nonce"])>BigInt(Number.MAX_SAFE_INTEGER)||BigInt(values["max-fee-quote-wei"])<=0n)stop("invalid nonce/fee limit");
  return values;
}
function assertExactApproval(authorization,env,state) {
  if(authorization?.mode!=="BROADCAST"||env?.GALILEO_ALLOW_BROADCAST!=="YES")stop("external broadcast acknowledgement required");
  const approved=authorization["approved-source"],external=env.GALILEO_USER_APPROVED_SOURCE;
  if(!/^[0-9a-f]{40}$/.test(approved||""))stop("approved source missing/invalid");
  if(external!==approved)stop("environment/CLI approved source mismatch");
  if(approved!==authorization["expected-source"])stop("approved source differs from expected-source");
  if(state && (state.source!==approved || !state.clean || !state.lineage || state.branch!=="feature/galileo-deployment-tooling" || state.tooling!==authorization["expected-tooling"]))stop("exact approved HEAD/tooling/clean branch mismatch");
}
function authorize(args,env) {
  // Deliberate operator acknowledgement is distinct from exact source approval.
  if(!Array.isArray(args)||args.filter(a=>a==="--broadcast").length!==1)stop("explicit --broadcast required");
  if(env?.GALILEO_ALLOW_BROADCAST!=="YES")stop("external broadcast acknowledgement required");
  const values=parse(args,"BROADCAST");assertExactApproval(values,env);return Object.freeze(values);
}
function authorizeReview(args){const values=parse(args,"REVIEW_ONLY");if(values["approved-source"])stop("read-only review cannot carry user approval");return Object.freeze(values);}
module.exports={authorize,authorizeReview,assertExactApproval,REVIEWED_PLAN};
