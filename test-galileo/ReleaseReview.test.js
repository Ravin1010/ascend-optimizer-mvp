"use strict";
const {expect}=require("chai");
const {authorize,REVIEWED_PLAN}=require("../scripts/galileo/release-policy");
const {publicExecution,readinessChecks,matchIdentity}=require("../scripts/galileo/release-review");
const {finalUserApprovalBarrier,futureSignerBoundary,FINAL_BARRIER}=require("../scripts/galileo/release-boundary");
const {identity}=require("../scripts/galileo/release-integrity");
const {hash}=require("../scripts/galileo/plan");
const actor="0x3e094d9068b48850f09Fc7cc70A7E24E5ed0442a";
const source="c2a48978e5d7baa1806a75fc0444a71bf8875afd",tooling="a".repeat(64),artifacts="b".repeat(64);
const env=()=>({GALILEO_ALLOW_BROADCAST:"YES",GALILEO_USER_APPROVED_SOURCE:source,get GALILEO_PRIVATE_KEY(){throw Error("SECRET MUST NEVER BE READ");}});
function fixture(){
 const now=Math.floor(Date.now()/1000);
 const values={"expected-chain":"16602","expected-deployer":actor,"expected-plan":REVIEWED_PLAN,"expected-source":source,"approved-source":source,"expected-tooling":tooling,"expected-artifacts":artifacts,"expected-nonce":"0","max-fee-quote-wei":"4000000007","review-expires-at":String(now+600)};
 const args=["--broadcast",...Object.entries(values).flatMap(([k,v])=>["--"+k,v])];
 const authorization=authorize(args,env());
 const state={source,tooling,branch:"feature/galileo-deployment-tooling",clean:true,lineage:true};
 const integrity={state,planHash:REVIEWED_PLAN,artifactHash:artifacts,bundle:{StrategyManager:{abi:["constructor(address initialOwner)"],bytecode:"0x60006000f3"}}};
 const methods=[];
 const provider={
  async send(method){methods.push(method);if(method!=="eth_chainId")throw Error("forbidden/unexpected RPC");return "0x40da";},
  async getBalance(){return 610000000000000000n;},async getTransactionCount(){return 0;},
  async getBlock(){return {number:1,hash:"0x"+"1".repeat(64),timestamp:now};},
  async getFeeData(){return {gasPrice:4000000007n};},async estimateGas(){return 875337n;}
 };
 return {args,authorization,provider,integrity,recheckSource:()=>state,methods,values};
}
async function rejects(fn,text){let e;try{await fn();}catch(error){e=error;}expect(e?.message).to.include(text);return e;}
function changed(f,key,value){const args=[...f.args];args[args.indexOf("--"+key)+1]=value;return args;}
describe("External Galileo release authorization — final barrier retained",function(){
 it("rejects missing broadcast before provider or secret access",()=>{const trap=new Proxy({}, {get(){throw Error("must not access");}});expect(()=>publicExecution({args:[],env:trap,provider:trap})).to.throw("--broadcast");});
 for(const acknowledgement of [undefined,"NO","yes",""])it(`rejects absent/wrong external acknowledgement ${String(acknowledgement)}`,()=>{const f=fixture();expect(()=>authorize(f.args,{GALILEO_ALLOW_BROADCAST:acknowledgement,get GALILEO_PRIVATE_KEY(){throw Error("secret");}})).to.throw("external broadcast acknowledgement");});
 it("rejects internally fabricated/missing authorization fields",()=>{const f=fixture();expect(()=>authorize(["--broadcast"],env())).to.throw("missing expected");expect(()=>authorize([...f.args,"--broadcast"],env())).to.throw("--broadcast");});
 for(const [key,value,message]of [["expected-chain","16661","chain"],["expected-deployer","0x0000000000000000000000000000000000000001","deployer"],["expected-plan","0".repeat(64),"plan fingerprint"]])it(`rejects wrong ${key}`,()=>{const f=fixture();expect(()=>authorize(changed(f,key,value),env())).to.throw(message);});
 for(const key of ["expected-source","expected-tooling"])it(`rejects mismatched ${key}`,async()=>{const f=fixture();let args=changed(f,key,key==="expected-source"?"1".repeat(40):"1".repeat(64));if(key==="expected-source"){args[args.indexOf("--approved-source")+1]="1".repeat(40);}f.authorization=authorize(args,key==="expected-source"?{GALILEO_ALLOW_BROADCAST:"YES",GALILEO_USER_APPROVED_SOURCE:"1".repeat(40)}:env());await rejects(()=>readinessChecks(f),key==="expected-source"?"approved source":"source/tooling fingerprint mismatch");});
 it("rejects wrong artifact fingerprint",async()=>{const f=fixture();f.integrity.artifactHash="0".repeat(64);await rejects(()=>readinessChecks(f),"artifact fingerprint");});
 for(const key of ["clean","lineage"])it(`rejects unsafe repository ${key}`,async()=>{const f=fixture();f.integrity.state[key]=false;await rejects(()=>readinessChecks(f),"source state");});
 it("rejects wrong actual chain before estimates",async()=>{const f=fixture();f.provider.send=async()=>"0x1";f.provider.estimateGas=()=>{throw Error("must not estimate");};await rejects(()=>readinessChecks(f),"wrong chain");});
 it("rejects insufficient balance",async()=>{const f=fixture();f.provider.getBalance=async()=>1n;await rejects(()=>readinessChecks(f),"insufficient balance");});
 it("rejects reserve breach",async()=>{const f=fixture();f.provider.getBalance=async()=>300000000000000000n;await rejects(()=>readinessChecks(f),"reserve breach");});
 it("rejects fee spike above external quote ceiling",async()=>{const f=fixture();f.provider.getFeeData=async()=>({gasPrice:8000000000n});await rejects(()=>readinessChecks(f),"fee spike");});
 it("rejects a fee spike during the final refresh",async()=>{const f=fixture();let n=0;f.provider.getFeeData=async()=>({gasPrice:++n<3?4000000007n:4000000008n});await rejects(()=>readinessChecks(f),"fee spike during review");});
 it("rejects nonce mismatch",async()=>{const f=fixture();f.provider.getTransactionCount=async()=>1;await rejects(()=>readinessChecks(f),"nonce mismatch");});
 it("rejects pending/mined nonce disagreement",async()=>{const f=fixture();f.provider.getTransactionCount=async(_,tag)=>tag==="pending"?0:1;await rejects(()=>readinessChecks(f),"nonce mismatch");});
 it("rejects a balance change during review",async()=>{const f=fixture();let reads=0;f.provider.getBalance=async()=>++reads<3?610000000000000000n:609000000000000000n;await rejects(()=>readinessChecks(f),"balance changed");});
 it("rejects nonce changes during review",async()=>{const f=fixture();let calls=0;f.provider.getTransactionCount=async()=>++calls>3?1:0;await rejects(()=>readinessChecks(f),"nonce");});
 it("rejects unknown configuration drift before provider/signer access",()=>{const f=fixture();expect(()=>publicExecution({args:f.args,env:env(),provider:f.provider,config:{native:"LIVE"}})).to.throw("configuration drift");});
 it("rejects attempted Ascend activation flag",()=>{const f=fixture();expect(()=>authorize([...f.args,"--activate-ascend","true"],env())).to.throw("unknown");});
 it("rejects Ascend/graph plan drift",async()=>{const f=fixture();f.integrity.planHash="0".repeat(64);await rejects(()=>readinessChecks(f),"plan/artifact fingerprint");});
 it("rejects stale review deadline",async()=>{const f=fixture();f.authorization=authorize(changed(f,"review-expires-at",String(Math.floor(Date.now()/1000)-1)),env());await rejects(()=>readinessChecks(f),"stale/excessive");});
 it("rejects excessive authorization lifetime",async()=>{const f=fixture();f.authorization=authorize(changed(f,"review-expires-at",String(Math.floor(Date.now()/1000)+10000)),env());await rejects(()=>readinessChecks(f),"stale/excessive");});
 it("rejects stale network snapshot",async()=>{const f=fixture();f.provider.getBlock=async()=>({hash:"0x1",timestamp:1});await rejects(()=>readinessChecks(f),"stale network");});
 it("rejects failed gas estimate without substituting rehearsal",async()=>{const f=fixture();f.provider.estimateGas=async()=>{throw Error("estimate fail");};await rejects(()=>readinessChecks(f),"gas estimate failure");});
 it("rejects material projected-spend growth",async()=>{const f=fixture();f.provider.estimateGas=async()=>100000000n;await rejects(()=>readinessChecks(f),"materially exceeds");});
 it("rejects source drift immediately before final barrier",async()=>{const f=fixture();f.recheckSource=()=>({...f.integrity.state,tooling:"0".repeat(64)});await rejects(()=>readinessChecks(f),"source/tooling");});
 it("passes all pre-signing checks and stops at final user barrier",async()=>{const f=fixture();const r=await readinessChecks(f);expect(r.balanceWei).to.equal("610000000000000000");expect(r.counts).to.deep.equal({DEPLOY:19,CONFIGURE:9,INTERACT:5});expect(r.planHash).to.equal(REVIEWED_PLAN);const e=await rejects(()=>Promise.resolve().then(()=>finalUserApprovalBarrier(r)),"separate user broadcast approval");expect(e.code).to.equal("SEPARATE_USER_APPROVAL_REQUIRED");expect(e.readiness.signerAccessed).to.equal(false);expect(e.readiness.transactionsSubmitted).to.equal(0);expect(f.methods.every(m=>m==="eth_chainId")).to.equal(true);});
 it("final barrier prevents future signer loader from running",async()=>{let calls=0;await rejects(()=>futureSignerBoundary({deployer:actor},async()=>{calls++;throw Error("must not create signer");}),"separate user broadcast approval");expect(calls).to.equal(0);});
 it("key/signer-like options are rejected without evaluating their getters",()=>{const f=fixture();let touched=false;expect(()=>publicExecution({args:f.args,env:env(),provider:f.provider,get signer(){touched=true;throw Error("secret");}})).to.throw("unsupported");expect(touched).to.equal(false);});
 it("artifact/source inspection reproduces the exact plan and compiler bundle",()=>{const i=identity();expect(i.planHash).to.equal(REVIEWED_PLAN);expect(i.artifactHash).to.equal(hash(i.bundle));expect(i.state.tooling).to.match(/^[a-f0-9]{64}$/);});
});
// Reusable read-only fixture; no real network or signing credential.
module.exports={fixture,env,source,actor};
