"use strict";
const {expect}=require("chai"),fs=require("node:fs"),os=require("node:os"),path=require("node:path");
const hre=require("hardhat");
const {Interface,keccak256,zeroPadValue,ZeroAddress}=require("ethers");
const fixtureBytes=require("./recovery-fixture");
const {ORIGINAL,recoveryAuthorization,assertRecoveryApproval}=require("../scripts/galileo/recovery-policy");
const {readOriginal,validateOriginal,validateRecoveryPrefix,sha256}=require("../scripts/galileo/recovery-validator");
const {loadArtifacts,SOURCE_FILES}=require("../scripts/galileo/release-integrity");
const {controlledPlan}=require("../scripts/galileo/controlled-plan");
const {validateResume,runLocal,engine,executionFingerprint}=require("../scripts/galileo/controlled-executor");
const {recoveryJournal,createRecoveryStore,assertNewTarget}=require("../scripts/galileo/recovery-journal");
const {recoveryReadiness,executeRecovery,matchRecovery}=require("../scripts/galileo/recovery-release");
const {recoverySignerBoundary,loadPrivateKeySigner,assertPermission}=require("../scripts/galileo/release-boundary");
const clone=structuredClone;
const actor=ORIGINAL.actor,source="a".repeat(40),tooling="b".repeat(64);
let bundle;
async function fails(fn,text){let error;try{await fn();}catch(e){error=e;}expect(error,"expected rejection").to.be.instanceOf(Error);if(text)expect(error.message).to.include(text);return error;}
function fixture(){
 const journal=JSON.parse(fixtureBytes()),review=controlledPlan(),now=Math.floor(Date.now()/1000);
 const blocks=new Map(journal.receipts.map(r=>[r.blockNumber,{hash:r.blockHash,number:r.blockNumber,timestamp:now}]));
 const transactions=new Map(journal.receipts.map(r=>[r.transactionHash,{hash:r.transactionHash,from:actor,nonce:r.nonce,to:null,data:r.calldata,value:BigInt(r.valueWei),gasLimit:BigInt(r.gasLimit),gasPrice:BigInt(r.effectiveGasPrice),chainId:16602n}]));
 const receipts=new Map(journal.receipts.map(r=>[r.transactionHash,{hash:r.transactionHash,status:1,blockHash:r.blockHash,blockNumber:r.blockNumber,contractAddress:r.deployedAddress,gasUsed:BigInt(r.gasUsed),gasPrice:BigInt(r.effectiveGasPrice)}]));
 const codes=new Map(),interfaces=new Map();
 journal.receipts.forEach((r,i)=>{
  const a=bundle[review.transactionSteps[i].contract];let code=a.deployedBytecode.slice(2);
  for(const refs of Object.values(a.immutableReferences))for(const loc of refs){const value=zeroPadValue(journal.receipts[0].deployedAddress,loc.length).slice(2);code=code.slice(0,loc.start*2)+value+code.slice((loc.start+loc.length)*2);}
  codes.set(r.deployedAddress.toLowerCase(),"0x"+code);interfaces.set(r.deployedAddress.toLowerCase(),new Interface(a.abi));
 });
 let historicalReads=0,submissions=0;
 const provider={
  send:async method=>{if(method==="eth_chainId")return "0x40da";submissions++;throw Error("forbidden RPC");},
  getTransaction:async h=>clone(transactions.get(h)),getTransactionReceipt:async h=>clone(receipts.get(h)),
  getBlock:async n=>n==="latest"?{number:60431000,hash:"0x"+"f".repeat(64),timestamp:now}:clone(blocks.get(n)),
  getCode:async a=>codes.get(a.toLowerCase())||"0x",
  getBalance:async(_,tag)=>{if(tag!==undefined&&tag!=="latest"){historicalReads++;throw Error("missing trie node");}return BigInt(ORIGINAL.balance);},
  getTransactionCount:async()=>3,getFeeData:async()=>({gasPrice:4000000007n}),estimateGas:async()=>1240951n,
  call:async tx=>{
   const iface=interfaces.get(tx.to.toLowerCase()),call=iface.parseTransaction({data:tx.data});
   const values={owner:actor,strategyCount:0n,isStrategyActive:false,strategyManager:journal.receipts[0].deployedAddress,rewardAccounting:ZeroAddress,paused:false,idleBalanceOf:0n,strategySharesOf:0n,withdrawalFeeInGwei:1n,totalDelegated:0n};
   if(!(call.name in values))throw Error("unexpected readback");return iface.encodeFunctionResult(call.name,[values[call.name]]);
  }
 };
 const state={source,tooling,parent:ORIGINAL.source,branch:ORIGINAL.branch,clean:true,lineage:true};
 const integrity={state,bundle,artifactHash:ORIGINAL.artifacts,planHash:ORIGINAL.plan};
 const fields={"expected-chain":"16602","expected-deployer":actor,"expected-plan":ORIGINAL.plan,"expected-source":source,"expected-tooling":tooling,"expected-artifacts":ORIGINAL.artifacts,"expected-nonce":"3","max-fee-quote-wei":"4000000007","review-expires-at":String(now+600)};
 const args=["--review-only",...Object.entries(fields).flatMap(([k,v])=>["--"+k,v])];
 const authorization=recoveryAuthorization(args,{});
 return {journal,review,provider,transactions,receipts,blocks,codes,integrity,authorization,args,fields,recheckSource:()=>state,historicalReads:()=>historicalReads,submissions:()=>submissions};
}
const validation=f=>validateRecoveryPrefix({provider:f.provider,bundle,review:f.review,journal:f.journal});
function broadcast(f){return {...f.authorization,mode:"BROADCAST","approved-source":source};}
const approval=()=>({GALILEO_ALLOW_BROADCAST:"YES",GALILEO_USER_APPROVED_SOURCE:source});
function temporary(f){const dir=fs.mkdtempSync(path.join(os.tmpdir(),"galileo-recovery-test-"));const originalFile=path.join(dir,"original.json"),target=path.join(dir,"recovery.json");fs.writeFileSync(originalFile,fixtureBytes());return {dir,originalFile,target,integrity:f.integrity,provider:f.provider,beforePersist(){}};}
describe("Explicit Galileo safe-stop recovery",function(){
 this.timeout(120000);
 before(()=>{bundle=loadArtifacts();});
 it("accepts the exact safe-stop bytes and independently validates the prefix",async()=>{const f=fixture();expect(sha256(fixtureBytes())).to.equal(ORIGINAL.sha256);expect(validateOriginal(f.journal)).to.equal(f.journal);const v=await validation(f);expect(v.nonce).to.equal(3);expect(v.state.validator).to.equal(f.journal.receipts[2].deployedAddress);});
 it("rejects journal SHA mismatch",()=>{const f=fixture(),t=temporary(f);try{fs.appendFileSync(t.originalFile," ");expect(()=>readOriginal(t.originalFile)).to.throw("SHA-256");}finally{fs.rmSync(t.dir,{recursive:true});}});
 for(const [label,mutate]of [
  ["sourceCommit",j=>j.sourceCommit="0".repeat(40)], ["original toolingHash",j=>j.toolingHash="0".repeat(64)],
  ["plan hash",j=>j.planHash="0".repeat(64)],["artifact hash",j=>j.artifactHash="0".repeat(64)],
  ["actor",j=>j.actor=ZeroAddress],["publicDeployer",j=>j.publicDeployer=ZeroAddress],
  ["receipt count",j=>j.receipts.pop()],["wrong step order",j=>j.receipts.reverse()],
  ["nonce history",j=>j.receipts[1].nonce=2],["pending intent",j=>j.pendingIntent={step:"nativeAdapter"}],
  ["missing failure",j=>delete j.failure],["wrong failure step",j=>j.failure.step="manager"],
  ["wrong failure status",j=>j.failure.status="FAILED"],["wrong failure code",j=>j.failure.errorCode="OTHER"],
  ["unexpected failure field",j=>j.failure.extra=true],["start nonce",j=>j.startNonce=1],
  ["reserve envelope",j=>j.reserveWei="1"],["initial envelope",j=>j.initialEnvelopeWei="1"]
 ])it("rejects "+label,async()=>{const f=fixture();mutate(f.journal);await fails(()=>validation(f));});
 for(const [label,mutate]of [
  ["missing receipt",f=>f.receipts.delete(f.journal.receipts[0].transactionHash)],
  ["failed receipt",f=>f.receipts.get(f.journal.receipts[0].transactionHash).status=0],
  ["noncanonical receipt",f=>f.blocks.get(f.journal.receipts[0].blockNumber).hash="0x00"],
  ["wrong receipt hash",f=>f.receipts.get(f.journal.receipts[0].transactionHash).hash="0x00"],
  ["transaction calldata",f=>f.transactions.get(f.journal.receipts[0].transactionHash).data="0x00"],
  ["transaction value",f=>f.transactions.get(f.journal.receipts[0].transactionHash).value=1n],
  ["transaction sender",f=>f.transactions.get(f.journal.receipts[0].transactionHash).from=ZeroAddress],
  ["transaction target",f=>f.transactions.get(f.journal.receipts[0].transactionHash).to=actor],
  ["deployment address",f=>f.receipts.get(f.journal.receipts[0].transactionHash).contractAddress=ZeroAddress],
  ["runtime bytecode",f=>f.codes.set(f.journal.receipts[0].deployedAddress.toLowerCase(),"0x6000")],
  ["gasUsed tampering",f=>f.journal.receipts[0].gasUsed="1"],
  ["effective gas price tampering",f=>f.journal.receipts[0].effectiveGasPrice="1"],
  ["gasCost tampering",f=>f.journal.receipts[0].gasCostWei="1"],
  ["cumulative spend tampering",f=>f.journal.receipts[0].cumulativeSpendWei="1"],
  ["wallet balance accounting tampering",f=>f.journal.receipts[0].walletBalanceAfterWei="1"],
  ["current balance mismatch",f=>f.provider.getBalance=async()=>BigInt(ORIGINAL.balance)+1n],
  ["pending nonce mismatch",f=>f.provider.getTransactionCount=async(_,tag)=>tag==="pending"?4:3],
  ["mined nonce mismatch",f=>f.provider.getTransactionCount=async(_,tag)=>tag==="latest"?2:3],
  ["nonce-3 code",f=>f.codes.set("0x13490b87030b31c5cd7d31408e59407b96e0a0ec","0x6000")],
  ["wrong chain",f=>f.provider.send=async()=>"0x1"],
  ["manager/vault/validator readback",f=>f.provider.call=async()=>"0x"+"00".repeat(32)]
 ])it("rejects "+label,async()=>{const f=fixture();mutate(f);await fails(()=>validation(f));});
 it("does not need historical balance state when all replacement checks pass",async()=>{const f=fixture();await validation(f);expect(f.historicalReads()).to.equal(0);});
 it("normal validator still rejects the failed journal",async()=>{const f=fixture();f.journal.toolingHash=executionFingerprint();await fails(()=>validateResume({provider:f.provider,bundle,review:f.review,sourceCommit:ORIGINAL.source,journal:f.journal,actor,expectedChain:16602,mode:"GALILEO"}),"ambiguous/failed");});
 it("review neither writes a journal, reads credentials, nor submits",async()=>{
  const f=fixture(),t=temporary(f);let accesses=0;
  const env=new Proxy({}, {get(_,k){if(k==="GALILEO_PRIVATE_KEY"){accesses++;throw Error("credential trap");}},ownKeys(){throw Error("no enumeration");}});
  try{const result=await executeRecovery({...f,env,readOriginalJournal:()=>readOriginal(t.originalFile),checkTarget:()=>assertNewTarget(t.originalFile,t.target),makeStore(){throw Error("review must not write");},loadSigner(){throw Error("review must not load signer");},armProvider(){throw Error("review must not arm");},runEngine(){throw Error("review must not execute");}});expect(result.status).to.equal("RECOVERY_READ_ONLY_REVIEW_PASSED");expect(result.signerAccessed).to.equal(false);expect(result.transactionsSubmitted).to.equal(0);expect(fs.existsSync(t.target)).to.equal(false);expect(accesses).to.equal(0);expect(f.submissions()).to.equal(0);expect(fs.readFileSync(t.originalFile).equals(fixtureBytes())).to.equal(true);}finally{fs.rmSync(t.dir,{recursive:true});}
 });
 it("creates separate explicit-version evidence retaining every original budget and prefix",async()=>{
  const f=fixture(),t=temporary(f);try{const store=await createRecoveryStore(t);const j=store.load();expect(j.version).to.equal("GALILEO_RECOVERY_V1");expect(j.originalJournalSha256).to.equal(ORIGINAL.sha256);expect(j.originalFailureMarker).to.deep.equal(f.journal.failure);expect(j.receipts).to.deep.equal(f.journal.receipts);for(const k of ["initialBalanceWei","reserveWei","feeCeilingWei","cumulativeSpendWei","initialEnvelopeWei","maxProjectedSpendWei"])expect(j[k]).to.equal(f.journal[k]);expect(j.recoveredPrefixLength).to.equal(3);expect(j.currentValidatedNonce).to.equal(3);expect(j.validationMethod).to.equal(ORIGINAL.method);const intent=store.load();intent.pendingIntent={step:"nativeAdapter",nonce:3,requestHash:"a".repeat(64)};store.save(intent);store.close();expect(fs.readFileSync(t.originalFile).equals(fixtureBytes())).to.equal(true);await fails(()=>createRecoveryStore(t),"unexpected recovery");}finally{fs.rmSync(t.dir,{recursive:true});}
 });
 it("refuses original journal as recovery target",async()=>{const f=fixture(),t=temporary(f);try{await fails(()=>createRecoveryStore({...t,target:t.originalFile}),"overwrite original");}finally{fs.rmSync(t.dir,{recursive:true});}});
 for(const suffix of [".lock",".tmp"])it("rejects ambiguous recovery target "+suffix,async()=>{const f=fixture(),t=temporary(f);try{fs.writeFileSync(t.target+suffix,"occupied");await fails(()=>createRecoveryStore(t),"unexpected recovery");}finally{fs.rmSync(t.dir,{recursive:true});}});
 it("does not create recovery evidence if validation fails",async()=>{const f=fixture(),t=temporary(f);try{f.provider.getBalance=async()=>0n;await fails(()=>createRecoveryStore(t));expect(fs.existsSync(t.target)).to.equal(false);}finally{fs.rmSync(t.dir,{recursive:true});}});
 it("detects original evidence changes before any recovery save",async()=>{const f=fixture(),t=temporary(f);try{const store=await createRecoveryStore(t);fs.appendFileSync(t.originalFile," ");expect(()=>store.save(store.load())).to.throw("SHA-256");store.close();}finally{fs.rmSync(t.dir,{recursive:true});}});
 it("rejects symlink evidence paths",()=>{const f=fixture(),t=temporary(f);try{const link=path.join(t.dir,"link.json");fs.symlinkSync(t.originalFile,link);expect(()=>readOriginal(link)).to.throw("symlink");}finally{fs.rmSync(t.dir,{recursive:true});}});
 it("requires exact NEW recovery source approval",()=>{const f=fixture(),a=broadcast(f);expect(()=>assertRecoveryApproval(a,approval(),f.integrity.state)).not.to.throw();for(const changed of [{...a,"approved-source":ORIGINAL.source},{...a,"expected-source":ORIGINAL.source},{...a,"approved-source":"c".repeat(40)}])expect(()=>assertRecoveryApproval(changed,approval(),f.integrity.state)).to.throw();});
 it("old external deployment approval cannot authorize recovery",()=>{const f=fixture();expect(()=>assertRecoveryApproval(broadcast(f),{...approval(),GALILEO_USER_APPROVED_SOURCE:ORIGINAL.source},f.integrity.state)).to.throw("new exact");});
 it("rejects resume selection and old expected-source in recovery parser",()=>{const f=fixture();expect(()=>recoveryAuthorization([...f.args,"--resume"],{})).to.throw("unsupported recovery");const args=f.args.map(x=>x===source?ORIGINAL.source:x);expect(()=>recoveryAuthorization(args,{})).to.throw("unsupported recovery");});
 it("rejects broadcast without explicit acknowledgement before credential access",()=>{const f=fixture();const args=f.args.map(x=>x==="--review-only"?"--broadcast":x);expect(()=>recoveryAuthorization([...args,"--approved-source",source],{})).to.throw("acknowledgement");});
 for(const field of ["source","tooling","parent","branch","clean"])it("rejects recovery source drift: "+field,()=>{const f=fixture();f.integrity.state[field]=field==="clean"?false:"unexpected";expect(()=>matchRecovery(f.authorization,f.integrity)).to.throw("recovery source");});
 it("retains one-read credential isolation and rejects a reintroduced synthetic credential",async()=>{
  const f=fixture(),a=broadcast(f),{readiness}=await recoveryReadiness({...f,authorization:a,original:f.journal});let reads=0;const env=approval();Object.defineProperty(env,"GALILEO_PRIVATE_KEY",{configurable:true,get(){reads++;return "0x"+"12".repeat(32);}});
  const grant=await recoverySignerBoundary(readiness,access=>loadPrivateKeySigner(env,{},access,()=>({getAddress:async()=>actor})),a,env,f.recheckSource);
  expect(reads).to.equal(1);expect("GALILEO_PRIVATE_KEY" in env).to.equal(false);assertPermission(grant.permission);env.GALILEO_PRIVATE_KEY="synthetic";expect(()=>assertPermission(grant.permission)).to.throw("isolation failed");
 });
 it("hands only a validated three-receipt recovery journal to shared continuation",async()=>{
  const f=fixture(),a=broadcast(f),env=approval();let continued=false,closed=false;
  const result=await executeRecovery({...f,authorization:a,env,readOriginalJournal:()=>clone(f.journal),checkTarget(){},makeStore:initial=>({load:()=>clone(initial),close(){closed=true;}}),loadSigner:async()=>({getAddress:async()=>actor}),armProvider:assertPermission,runEngine:async options=>{continued=true;expect(options.expectedNonce).to.equal(3);expect(options.store.load().receipts.map(r=>r.step)).to.deep.equal(["manager","vault","validator"]);const state=await options.validateExisting({journal:options.store.load()});expect(state.manager).to.equal(f.journal.receipts[0].deployedAddress);await options.beforeStep();return {nextStep:options.review.transactionSteps[options.store.load().receipts.length].name};}});
  expect(result.nextStep).to.equal("nativeAdapter");expect(continued&&closed).to.equal(true);expect(f.submissions()).to.equal(0);
 });
 it("covers every production recovery file in the tooling fingerprint",()=>{const files=fs.readdirSync(path.resolve(__dirname,"../scripts/galileo")).filter(n=>n.startsWith("recovery-")&&n.endsWith(".js"));expect(files.length).to.be.greaterThan(0);for(const name of files)expect(SOURCE_FILES).to.include("scripts/galileo/"+name);});
 it("shared engine continues a local three-step prefix without duplicate deployments",async()=>{
  await hre.network.provider.send("hardhat_reset");let value=null;const store={load:()=>clone(value),save:j=>{value=clone(j);}};
  const prefix=await runLocal({hre,sourceCommit:"local-recovery-test",store,maxSteps:3});const first=prefix.journal.receipts.map(r=>r.transactionHash);value.version="GALILEO_RECOVERY_V1";value.toolingHash=executionFingerprint();
  const localBundle=await require("../scripts/galileo/controlled-executor").artifactsFor(hre,controlledPlan().plan);const [signer]=await hre.ethers.getSigners();
  const completed=await engine({provider:hre.ethers.provider,signer,actor:signer.address,bundle:localBundle,review:controlledPlan(),sourceCommit:"local-recovery-test",store,expectedChain:31337,mode:"LOCAL_ONLY",expectedNonce:3,validateExisting:async()=>prefix.state});
  expect(completed.journal.receipts).to.have.length(33);expect(completed.journal.receipts.slice(0,3).map(r=>r.transactionHash)).to.deep.equal(first);expect(completed.journal.receipts[3].step).to.equal("nativeAdapter");expect(completed.journal.receipts[3].nonce).to.equal(3);expect(new Set(completed.journal.receipts.map(r=>r.transactionHash)).size).to.equal(33);expect(completed.journal.reserveWei).to.equal(prefix.journal.reserveWei);expect(completed.journal.maxProjectedSpendWei).to.equal(prefix.journal.maxProjectedSpendWei);
 });
});

describe("Deferred recovery pending-intent persistence correction",function(){
 this.timeout(120000);
 before(()=>{bundle=loadArtifacts();});
 const absent=t=>{for(const suffix of ["",".lock",".tmp"])expect(fs.existsSync(t.target+suffix),"unexpected recovery evidence "+suffix).to.equal(false);};
 const intent=store=>({...store.load(),pendingIntent:{step:"nativeAdapter",nonce:3,requestHash:"a".repeat(64)}});
 async function scope(fn){const f=fixture(),t=temporary(f);try{await fn(f,t);}finally{fs.rmSync(t.dir,{recursive:true});}}
 function flow(f,t,overrides={}){
  const env={...approval(),GALILEO_PRIVATE_KEY:"0x"+"12".repeat(32)};
  const signer={getAddress:async()=>actor,sendTransaction:async()=>{throw Error("fake signer must not be reached");}};
  return {...f,authorization:broadcast(f),env,
   readOriginalJournal:()=>readOriginal(t.originalFile),checkTarget:()=>assertNewTarget(t.originalFile,t.target),
   makeStore:(_initial,beforePersist)=>createRecoveryStore({...t,beforePersist}),
   loadSigner:access=>loadPrivateKeySigner(env,{},access,()=>signer),armProvider:assertPermission,runEngine:engine,...overrides};
 }
 for(const suffix of ["",".lock",".tmp"])it("construction creates no "+(suffix||"target"),()=>scope(async(f,t)=>{const store=await createRecoveryStore(t);expect(fs.existsSync(t.target+suffix)).to.equal(false);store.close();}));
 it("load returns a defensive exact in-memory recovery prefix",()=>scope(async(f,t)=>{const store=await createRecoveryStore(t);const j=store.load();expect(j.receipts).to.deep.equal(f.journal.receipts);expect(j.version).to.equal("GALILEO_RECOVERY_V1");j.receipts.pop();expect(store.load().receipts).to.have.length(3);absent(t);store.close();}));
 it("close before persistence is an idempotent no-op with no files",()=>scope(async(f,t)=>{const store=await createRecoveryStore(t);store.close();store.close();absent(t);}));
 for(const [label,modify]of [
  ["missing approval",o=>delete o.env.GALILEO_ALLOW_BROADCAST],
  ["approval mismatch",o=>o.env.GALILEO_USER_APPROVED_SOURCE=ORIGINAL.source],
  ["missing credential",o=>delete o.env.GALILEO_PRIVATE_KEY],
  ["malformed credential",o=>o.env.GALILEO_PRIVATE_KEY="invalid synthetic fixture"],
  ["throwing credential getter",o=>Object.defineProperty(o.env,"GALILEO_PRIVATE_KEY",{configurable:true,get(){throw Error("synthetic credential getter failure");}})],
  ["credential cleanup failure",o=>Object.defineProperty(o.env,"GALILEO_PRIVATE_KEY",{configurable:false,value:"0x"+"12".repeat(32)})],
  ["signer mismatch",o=>o.loadSigner=access=>loadPrivateKeySigner(o.env,{},access,()=>({getAddress:async()=>ZeroAddress}))]
 ])it(label+" leaves no recovery journal/lock/tmp",()=>scope(async(f,t)=>{const o=flow(f,t);modify(o);await fails(()=>executeRecovery(o));absent(t);expect(fs.readFileSync(t.originalFile).equals(fixtureBytes())).to.equal(true);}));
 it("approval expiring at the credential boundary leaves no files",()=>scope(async(f,t)=>{const o=flow(f,t),make=o.makeStore;o.makeStore=async(...args)=>{const s=await make(...args);o.authorization["review-expires-at"]=String(Math.floor(Date.now()/1000)-1);return s;};await fails(()=>executeRecovery(o),"expired");absent(t);}));
 it("source recheck fails before credential access without materialization",()=>scope(async(f,t)=>{const o=flow(f,t);let reads=0,calls=0;Object.defineProperty(o.env,"GALILEO_PRIVATE_KEY",{configurable:true,get(){reads++;throw Error("must not read");}});o.recheckSource=()=>({...f.integrity.state,source:++calls>=3?"c".repeat(40):source});await fails(()=>executeRecovery(o));expect(reads).to.equal(0);absent(t);}));
 it("changed original evidence before credential access leaves no recovery files",()=>scope(async(f,t)=>{const o=flow(f,t);let calls=0,reads=0;Object.defineProperty(o.env,"GALILEO_PRIVATE_KEY",{configurable:true,get(){reads++;throw Error("must not read");}});o.readOriginalJournal=()=>{if(++calls===4)fs.appendFileSync(t.originalFile," ");return readOriginal(t.originalFile);};await fails(()=>executeRecovery(o));expect(reads).to.equal(0);absent(t);}));
 it("current-state validation failure leaves no recovery files",()=>scope(async(f,t)=>{f.provider.getBalance=async()=>0n;await fails(()=>executeRecovery(flow(f,t)));absent(t);}));
 it("target appearing after construction is preserved without overwrite or signing",()=>scope(async(f,t)=>{const o=flow(f,t),make=o.makeStore;let signed=0;o.makeStore=async(...args)=>{const s=await make(...args);fs.writeFileSync(t.target,"external target");return s;};o.loadSigner=async()=>({getAddress:async()=>actor,sendTransaction:async()=>signed++});delete o.env.GALILEO_PRIVATE_KEY;await fails(()=>executeRecovery(o));expect(signed).to.equal(0);expect(fs.readFileSync(t.target,"utf8")).to.equal("external target");expect(fs.existsSync(t.target+".lock")).to.equal(false);}));
 for(const [label,change]of [
  ["step-4 state verification",(f,state)=>{f.provider.call=async()=>"0x"+"00".repeat(32);return state;}],
  ["step-4 construction",(_f,state)=>({...state,owner:undefined})],
  ["step-4 estimateGas",(f,state)=>{f.provider.estimateGas=async()=>{throw Error("synthetic estimate failure");};return state;}],
  ["step-4 cumulative budget guard",(f,state)=>{f.provider.estimateGas=async()=>10n**12n;return state;}],
  ["execution permission before pending intent",(f,state)=>{f.provider.estimateGas=async()=>{f.integrity.state.source="c".repeat(40);return 1240951n;};return state;}]
 ])it(label+" failure creates no recovery evidence",()=>scope(async(f,t)=>{let signed=0;const o=flow(f,t);o.loadSigner=access=>loadPrivateKeySigner(o.env,{},access,()=>({getAddress:async()=>actor,sendTransaction:async()=>signed++}));o.runEngine=async options=>{const original=options.validateExisting;return engine({...options,validateExisting:async args=>change(f,await original(args))});};await fails(()=>executeRecovery(o));expect(signed).to.equal(0);absent(t);}));
 it("changed original evidence during step-4 checks prevents materialization",()=>scope(async(f,t)=>{const o=flow(f,t);o.runEngine=async options=>{const original=options.validateExisting;return engine({...options,validateExisting:async args=>{const state=await original(args);f.provider.estimateGas=async()=>{fs.appendFileSync(t.originalFile," ");return 1240951n;};return state;}});};await fails(()=>executeRecovery(o));absent(t);}));
 for(const [label,modify]of [
  ["arbitrary content",()=>({unrelated:true})],
  ["no pending intent",(_j,s)=>s.load()],
  ["wrong step",j=>({...j,pendingIntent:{...j.pendingIntent,step:"manager"}})],
  ["wrong nonce",j=>({...j,pendingIntent:{...j.pendingIntent,nonce:4}})],
  ["premature transaction hash",j=>({...j,pendingIntent:{...j.pendingIntent,transactionHash:"0x00"}})],
  ["malformed request hash",j=>({...j,pendingIntent:{...j.pendingIntent,requestHash:"bad"}})],
  ["changed prefix",j=>({...j,receipts:j.receipts.slice(1)})],
  ["changed budget",j=>({...j,reserveWei:"0"})],
  ["pre-intent failure marker",j=>({...j,failure:{status:"STOPPED"}})]
 ])it("rejects first save with "+label+" without files",()=>scope(async(f,t)=>{const store=await createRecoveryStore(t);expect(()=>store.save(modify(intent(store),store))).to.throw();absent(t);store.close();}));
 it("genuine pending intent is the first durable recovery state, with exact prefix and provenance",()=>scope(async(f,t)=>{const store=await createRecoveryStore(t);const value=intent(store);store.save(value);const disk=JSON.parse(fs.readFileSync(t.target));expect(disk.version).to.equal("GALILEO_RECOVERY_V1");expect(disk.pendingIntent).to.deep.equal(value.pendingIntent);expect(disk.receipts).to.deep.equal(f.journal.receipts);expect(disk.originalJournalSha256).to.equal(ORIGINAL.sha256);expect(fs.existsSync(t.target+".lock")).to.equal(true);expect(fs.existsSync(t.target+".tmp")).to.equal(false);expect(fs.readFileSync(t.originalFile).equals(fixtureBytes())).to.equal(true);store.close();}));
 it("subsequent persistence remains atomic, locked and protects provenance",()=>scope(async(f,t)=>{const store=await createRecoveryStore(t);const value=intent(store);store.save(value);const next=store.load();next.pendingIntent.transactionHash="0x"+"1".repeat(64);store.save(next);expect(JSON.parse(fs.readFileSync(t.target)).pendingIntent.transactionHash).to.equal(next.pendingIntent.transactionHash);expect(fs.existsSync(t.target+".lock")).to.equal(true);expect(fs.existsSync(t.target+".tmp")).to.equal(false);expect(()=>assertNewTarget(t.originalFile,t.target)).to.throw();expect(()=>store.save({...next,maxProjectedSpendWei:"0"})).to.throw("provenance");store.close();expect(fs.existsSync(t.target+".lock")).to.equal(false);}));
 it("checks permission immediately before first materialization",()=>scope(async(f,t)=>{const store=await createRecoveryStore({...t,beforePersist(){throw Error("synthetic permission revoked");}});expect(()=>store.save(intent(store))).to.throw("permission revoked");absent(t);store.close();}));
 it("first durable-save failure prevents signing and cannot be retried",()=>scope(async(f,t)=>{const o=flow(f,t);let signed=0,armed=false;const originalFsync=fs.fsyncSync;o.armProvider=p=>{assertPermission(p);armed=true;};o.loadSigner=access=>loadPrivateKeySigner(o.env,{},access,()=>({getAddress:async()=>actor,sendTransaction:async()=>signed++}));fs.fsyncSync=()=>{throw Error("synthetic durable-save failure");};try{await fails(()=>executeRecovery(o));expect(armed).to.equal(true);expect(signed).to.equal(0);}finally{fs.fsyncSync=originalFsync;}}));
 it("shared engine reaches fake signing only after durable nativeAdapter intent and pre-signing recheck",()=>scope(async(f,t)=>{const o=flow(f,t);let signed=0,fsyncs=0,rechecks=0;const originalFsync=fs.fsyncSync;fs.fsyncSync=fd=>{fsyncs++;return originalFsync(fd);};o.recheckSource=()=>{rechecks++;return f.integrity.state;};o.loadSigner=access=>loadPrivateKeySigner(o.env,{},access,()=>({getAddress:async()=>actor,sendTransaction:async()=>{signed++;const disk=JSON.parse(fs.readFileSync(t.target));expect(disk.pendingIntent.step).to.equal("nativeAdapter");expect(disk.pendingIntent.nonce).to.equal(3);expect(disk.pendingIntent).not.to.have.property("transactionHash");expect(disk.receipts).to.have.length(3);expect(fsyncs).to.be.at.least(2);expect(rechecks).to.be.at.least(5);expect(fs.existsSync(t.target+".lock")).to.equal(true);throw Error("synthetic post-intent stop; never signs or sends");}}));try{await fails(()=>executeRecovery(o));expect(signed).to.equal(1);const disk=JSON.parse(fs.readFileSync(t.target));expect(disk.pendingIntent.step).to.equal("nativeAdapter");expect(disk.failure.status).to.equal("STOPPED");expect(fs.readFileSync(t.originalFile).equals(fixtureBytes())).to.equal(true);}finally{fs.fsyncSync=originalFsync;}}));
});
