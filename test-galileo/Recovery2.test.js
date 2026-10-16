"use strict";
const {expect}=require("chai"),fs=require("node:fs"),path=require("node:path"),hre=require("hardhat");
const {keccak256,ZeroAddress,id}=require("ethers");
const H=require("./recovery2-helpers");
const {ORIGINAL}=require("../scripts/galileo/recovery-policy"),{S2,stage2Authorization,assertStage2Approval}=require("../scripts/galileo/recovery2-policy");
const {readPredecessors,validateStage1,validateStage2,historicalRequest,assertHistoricalRequest,json}=require("../scripts/galileo/recovery2-validator");
const {createStage2Store,assertStage2Target}=require("../scripts/galileo/recovery2-journal");
const {exactReplayGuard,resolveStep24,continueStage2}=require("../scripts/galileo/recovery2-executor");
const {stage2Readiness,executeStage2}=require("../scripts/galileo/recovery2-release");
const {loadPrivateKeySigner,assertPermission}=require("../scripts/galileo/release-boundary");
const {SOURCE_FILES}=require("../scripts/galileo/release-integrity");
const {hash,IDS}=require("../scripts/galileo/plan");
const {controlledPlan}=require("../scripts/galileo/controlled-plan");
const actor=ORIGINAL.actor,source="c".repeat(40);
const validation=f=>validateStage2({provider:f.provider,bundle:f.bundle,review:f.review,evidence:f.readEvidence()});
async function fails(fn,text){let error;try{await fn();}catch(e){error=e;}expect(error,"expected rejection").to.be.instanceOf(Error);if(text)expect(error.message).to.include(text);return error;}
async function scope(fn,mode=S2.replay){const f=H.fixture(mode),t=H.temp(f);try{return await fn(f,t);}finally{fs.rmSync(t.dir,{recursive:true});}}
function absent(t){for(const suffix of ["",".lock",".tmp"])expect(fs.existsSync(t.target+suffix)).to.equal(false);}
function flow(f,t,extra={}){
 const env={GALILEO_ALLOW_BROADCAST:"YES",GALILEO_USER_APPROVED_SOURCE:source,GALILEO_PRIVATE_KEY:"0x"+"34".repeat(32)};
 return {...f,authorization:{...f.authorization,mode:"BROADCAST","approved-source":source},env,readEvidence:t.readEvidence,checkTarget:()=>assertStage2Target(t.target,t.protectedFiles),makeStore:beforePersist=>createStage2Store({...t,beforePersist}),loadSigner:access=>loadPrivateKeySigner(env,{},access,()=>({getAddress:async()=>actor,sendTransaction:async()=>{throw Error("fake transport stops");}})),armProvider:assertPermission,...extra};
}
describe("Stage-2 exact ambiguous-intent recovery",function(){
 this.timeout(240000);
 before(H.setup);
 for(const file of ["originalFile","stage1File"])it("requires exact predecessor SHA: "+file,()=>scope(async(f,t)=>{fs.appendFileSync(t[file]," ");expect(()=>t.readEvidence()).to.throw("SHA-256");}));
 for(const [label,change]of [
  ["source",j=>j.sourceCommit="0".repeat(40)],["Stage-1 recovery source",j=>j.recoverySourceCommit="0".repeat(40)],
  ["Stage-1 tooling",j=>j.recoveryToolingFingerprint="0".repeat(64)],["execution fingerprint",j=>j.toolingHash="0".repeat(64)],
  ["plan",j=>j.planHash="0".repeat(64)],["artifact",j=>j.artifactHash="0".repeat(64)],["actor",j=>j.actor=ZeroAddress],
  ["count",j=>j.receipts.pop()],["nonce history",j=>j.receipts[5].nonce=4],["duplicate hashes",j=>j.receipts[5].transactionHash=j.receipts[4].transactionHash],
  ["receipt order",j=>j.receipts[4].step="manager"],["last transaction",j=>j.receipts[22].transactionHash="0x"+"0".repeat(64)],
  ["cumulative spend",j=>j.cumulativeSpendWei="0"],["initial balance",j=>j.initialBalanceWei="1"],["reserve",j=>j.reserveWei="1"],["maximum spend",j=>j.maxProjectedSpendWei="1"],
  ["missing pending intent",j=>delete j.pendingIntent],["wrong pending step",j=>j.pendingIntent.step="register1"],["wrong pending nonce",j=>j.pendingIntent.nonce=24],["pending request hash",j=>j.pendingIntent.requestHash="0".repeat(64)],
  ["missing failure",j=>delete j.failure],["failure status",j=>j.failure.status="FAILED"],["failure code",j=>j.failure.errorCode="OTHER"],["failure step",j=>j.failure.step="register1"],
  ["original prefix mutation",j=>j.receipts[0].gasCostWei="0"]
 ])it("rejects Stage-1 "+label,async()=>{const f=H.fixture();change(f.stage1);await fails(()=>validation(f));});
 for(const [label,change]of [
  ["missing transaction",f=>f.transactions.delete(f.stage1.receipts[4].transactionHash)],["missing receipt",f=>f.receipts.delete(f.stage1.receipts[4].transactionHash)],
  ["failed receipt",f=>f.receipts.get(f.stage1.receipts[4].transactionHash).status=0],["noncanonical receipt",f=>f.blocks.get(f.stage1.receipts[4].blockNumber).hash="bad"],
  ["wrong sender",f=>f.transactions.get(f.stage1.receipts[4].transactionHash).from=ZeroAddress],["wrong target",f=>f.transactions.get(f.stage1.receipts[10].transactionHash).to=ZeroAddress],
  ["wrong calldata",f=>f.transactions.get(f.stage1.receipts[4].transactionHash).data="0x"],["wrong value",f=>f.transactions.get(f.stage1.receipts[4].transactionHash).value=1n],
  ["runtime drift",f=>f.codes.set(f.stage1.receipts[4].deployedAddress.toLowerCase(),"0x6000")],["deployment address",f=>f.receipts.get(f.stage1.receipts[4].transactionHash).contractAddress=ZeroAddress],
  ["gasUsed accounting",f=>f.stage1.receipts[4].gasUsed="1"],["gas price accounting",f=>f.stage1.receipts[4].effectiveGasPrice="1"],["gas cost accounting",f=>f.stage1.receipts[4].gasCostWei="1"],
  ["per-step cumulative accounting",f=>f.stage1.receipts[4].cumulativeSpendWei="1"],["wallet accounting",f=>f.stage1.receipts[4].walletBalanceAfterWei="1"],
  ["wrong chain",f=>f.provider.send=async()=>"0x1"]
 ])it("rejects prefix "+label,async()=>{const f=H.fixture();change(f);await fails(()=>validation(f));});
 it("accepts exact MODE A with all 23 receipts, 19 deployments and no historical balance reads",async()=>{const f=H.fixture(),v=await validation(f);expect(v.mode).to.equal(S2.replay);expect(v.nonce).to.equal(23);expect(Object.keys(v.state.artifactNames)).to.have.length(20);expect(f.historicalReads).to.equal(0);});
 for(const [pending,mined]of [[24,23],[25,25],[22,22],[23,24],[24,25],[0,0]])it(`rejects nonce state ${pending}/${mined}`,async()=>{const f=H.fixture();f.pending=pending;f.mined=mined;await fails(()=>validation(f),"nonce state");});
 for(const [label,change]of [
  ["registration count",f=>f.count=1n],["Native pre-registered",f=>f.callOverride=(target,call)=>target===S2.manager.toLowerCase()&&call.name==="isStrategyActive"&&call.args[0]===S2.nativeId?true:undefined],
  ["vault idle",f=>f.callOverride=(_,call)=>call.name==="idleBalanceOf"?1n:undefined],["strategy shares",f=>f.callOverride=(_,call)=>call.name==="strategySharesOf"?1n:undefined],
  ["validator delegation",f=>f.callOverride=(_,call)=>call.name==="totalDelegated"?1n:undefined],["wallet balance",f=>f.balance+=1n],
  ["ownership",f=>f.callOverride=(_,call)=>call.name==="owner"?ZeroAddress:undefined]
 ])it("rejects MODE A "+label+" drift",async()=>{const f=H.fixture();change(f);await fails(()=>validation(f));});
 it("reconstructs the exact calldata and historical JSON request hash without a search",async()=>{const f=H.fixture(),v=await validation(f);expect(keccak256(v.request.data)).to.equal(S2.calldataHash);expect(hash(json(v.request))).to.equal(S2.requestHash);expect(v.built.args[0]).to.equal(S2.nativeId);});
 for(const [field,value]of [["gasLimit",182779n],["gasPrice",8000000015n],["to",ZeroAddress],["value",1n],["chainId",31337],["nonce",24],["data","0x"],["from",ZeroAddress]])it("rejects a historical replacement field: "+field,async()=>{const f=H.fixture(),v=await validation(f);expect(()=>assertHistoricalRequest({...v.request,[field]:value})).to.throw("historical");});
 it("rejects arbitrary additional request fields",async()=>{const f=H.fixture(),v=await validation(f);expect(()=>assertHistoricalRequest({...v.request,maxFeePerGas:1n})).to.throw("historical");});
 it("accepts fresh estimate and preserves exact historical gas fields even if quote decreases",async()=>{const f=H.fixture(),v=await validation(f);f.provider.getFeeData=async()=>({gasPrice:1n});const g=await exactReplayGuard({provider:f.provider,validated:v,journal:f.stage1,bundle:f.bundle,review:f.review,maxQuote:S2.maxQuote});expect(g.gasLimit).to.equal(182778n);expect(g.gasPrice).to.equal(8000000014n);});
 for(const [label,change]of [
  ["estimate above historical limit",f=>f.provider.estimateGas=async()=>182779n],
  ["margin above historical limit",f=>f.provider.estimateGas=async()=>152316n],
  ["fee quote above policy",f=>f.provider.getFeeData=async()=>({gasPrice:4000000008n})],
  ["base fee above historical price",f=>{const get=f.provider.getBlock;f.provider.getBlock=async tag=>({...await get(tag),baseFeePerGas:8000000015n});}],
  ["estimate RPC failure",f=>f.provider.estimateGas=async()=>{throw Error("synthetic estimate failure");}]
 ])it("rejects unsafe exact replay: "+label,async()=>{const f=H.fixture(),v=await validation(f);change(f);await fails(()=>exactReplayGuard({provider:f.provider,validated:v,journal:f.stage1,bundle:f.bundle,review:f.review,maxQuote:S2.maxQuote}));});
 it("accepts exact MODE B and marks its canonical receipt adopted",async()=>{const f=H.fixture(S2.adopt),v=await validation(f);expect(v.mode).to.equal(S2.adopt);expect(v.nonce).to.equal(24);expect(v.adoptedRecord.adoption).to.equal(S2.adoption);expect(v.adoptedRecord.nonce).to.equal(23);});
 for(const [label,change]of [
  ["wrong sender",f=>f.candidate.from=ZeroAddress],["wrong target",f=>f.candidate.to=ZeroAddress],["wrong calldata",f=>f.candidate.data="0x00"],
  ["wrong gas limit",f=>f.candidate.gasLimit=182779n],["wrong gas price",f=>f.candidate.gasPrice=8000000015n],["wrong value",f=>f.candidate.value=1n],
  ["wrong chain",f=>f.candidate.chainId=31337n],["wrong fee envelope",f=>f.candidate.maxFeePerGas=8000000015n],
  ["failed receipt",f=>f.adoptedReceipt.status=0],["missing receipt",f=>f.receipts.delete(f.candidate.hash)],
  ["noncanonical receipt",f=>f.adoptedReceipt.blockHash="0x00"],["missing candidate",f=>f.candidates=[]],
  ["multiple candidates",f=>f.candidates.push({...f.candidate,hash:"0x"+"c".repeat(64)})],
  ["registration configuration",f=>f.registration.depositCap=1n],["inactive Native",f=>f.registration.active=false],["extra registration",f=>f.count=2n],
  ["unexpected vault activity",f=>f.callOverride=(_,c)=>c.name==="idleBalanceOf"?1n:undefined],
  ["unexpected shares",f=>f.callOverride=(_,c)=>c.name==="strategySharesOf"?1n:undefined],
  ["unexpected delegation",f=>f.callOverride=(_,c)=>c.name==="totalDelegated"?1n:undefined],
  ["balance mismatch",f=>f.balance+=1n]
 ])it("rejects MODE B "+label,async()=>{const f=H.fixture(S2.adopt);change(f);await fails(()=>validation(f));});
 for(const mode of [S2.replay,S2.adopt])it("review in "+mode+" cannot access credential/arm/create evidence",()=>scope(async(f,t)=>{const env=new Proxy({}, {get(){throw Error("synthetic secret must not be touched");},ownKeys(){throw Error("environment enumeration forbidden");}});const o=flow(f,t,{authorization:f.authorization,env,makeStore(){throw Error("review cannot create store");},loadSigner(){throw Error("review cannot load signer");},armProvider(){throw Error("review cannot arm");}});const result=await executeStage2(o);expect(result.status).to.equal("RECOVERY2_READ_ONLY_REVIEW_PASSED");expect(result.signerAccessed).to.equal(false);expect(f.submissions).to.equal(0);absent(t);},mode));
 for(const suffix of ["",".lock",".tmp"])it("rejects existing Stage-2 target "+suffix,()=>scope(async(f,t)=>{fs.writeFileSync(t.target+suffix,"occupied");await fails(()=>createStage2Store(t));expect(fs.readFileSync(t.target+suffix,"utf8")).to.equal("occupied");}));
 it("deferred construction/load/close creates no files and retains original budgets",()=>scope(async(f,t)=>{const s=await createStage2Store(t),j=s.load();expect(j.version).to.equal("GALILEO_RECOVERY2_V1");expect(j.receipts).to.deep.equal(f.stage1.receipts);expect(j.stage1PendingIntent).to.deep.equal(f.stage1.pendingIntent);for(const key of ["reserveWei","maxProjectedSpendWei","initialBalanceWei","feeCeilingWei","cumulativeSpendWei"])expect(j[key]).to.equal(f.stage1[key]);j.receipts.pop();expect(s.load().receipts).to.have.length(23);s.close();absent(t);}));
 for(const [label,change]of [
  ["arbitrary first state",()=>({})],["wrong step",j=>({...j,pendingIntent:{step:"register1",nonce:23,requestHash:S2.requestHash}})],
  ["wrong nonce",j=>({...j,pendingIntent:{step:"register0",nonce:24,requestHash:S2.requestHash}})],["wrong request hash",j=>({...j,pendingIntent:{step:"register0",nonce:23,requestHash:"0".repeat(64)}})],
  ["premature tx hash",j=>({...j,pendingIntent:{step:"register0",nonce:23,requestHash:S2.requestHash,transactionHash:"0x00"}})]
 ])it("rejects first persistence: "+label,()=>scope(async(f,t)=>{const s=await createStage2Store(t);expect(()=>s.save(change(s.load()))).to.throw();absent(t);s.close();}));
 it("persists only an exact pending intent before replay",()=>scope(async(f,t)=>{const s=await createStage2Store(t),j=s.load();j.pendingIntent={step:"register0",nonce:23,requestHash:S2.requestHash};s.save(j);expect(JSON.parse(fs.readFileSync(t.target)).pendingIntent).to.deep.equal(j.pendingIntent);expect(fs.existsSync(t.target+".lock")).to.equal(true);s.close();expect(t.readEvidence().stage1).to.deep.equal(f.stage1);}));
 it("durably adopts without any nonce-23 signing",()=>scope(async(f,t)=>{const s=await createStage2Store(t),v=await validation(f);let signed=0;const r=await resolveStep24({provider:f.provider,signer:{sendTransaction:async()=>signed++},store:s,bundle:f.bundle,revalidate:()=>validation(f),checkPermission(){},maxQuote:S2.maxQuote});expect(signed).to.equal(0);expect(r.journal.receipts).to.have.length(24);expect(r.journal.adoption).to.equal(S2.adoption);expect(r.journal.pendingIntent).to.equal(null);expect(JSON.parse(fs.readFileSync(t.target)).receipts).to.have.length(24);s.close();},S2.adopt));
 for(const field of ["originalFile","stage1File"])it("pins "+field+" before every persistence",()=>scope(async(f,t)=>{const s=await createStage2Store(t);fs.appendFileSync(t[field]," ");const j=s.load();j.pendingIntent={step:"register0",nonce:23,requestHash:S2.requestHash};expect(()=>s.save(j)).to.throw("SHA-256");absent(t);s.close();}));
 it("credential failure leaves no Stage-2 journal and sanitizes phase evidence",()=>scope(async(f,t)=>{const o=flow(f,t);o.env.GALILEO_PRIVATE_KEY="SYNTHETIC_DO_NOT_LOG";const error=await fails(()=>executeStage2(o));expect(error.phase).to.equal("SIGNER_BOUNDARY");expect(error.message).not.to.include("SYNTHETIC_DO_NOT_LOG");absent(t);}));
 for(const old of [ORIGINAL.source,S2.parent])it("rejects old source approval "+old,async()=>{const f=H.fixture(),a={...f.authorization,mode:"BROADCAST","approved-source":old};expect(()=>assertStage2Approval(a,{GALILEO_ALLOW_BROADCAST:"YES",GALILEO_USER_APPROVED_SOURCE:old},f.integrity.state)).to.throw();});
 it("requires exact new source, parent, branch, approval and tooling",()=>{const f=H.fixture(),a={...f.authorization,mode:"BROADCAST","approved-source":source},env={GALILEO_ALLOW_BROADCAST:"YES",GALILEO_USER_APPROVED_SOURCE:source};expect(()=>assertStage2Approval(a,env,f.integrity.state)).not.to.throw();for(const key of ["source","parent","branch","tooling","clean"]){const s={...f.integrity.state,[key]:key==="clean"?false:"bad"};expect(()=>assertStage2Approval(a,env,s)).to.throw();}});
 it("rejects --resume and old expected source in Stage-2 CLI",()=>{const f=H.fixture(),args=["--review-only",...Object.entries(f.authorization).filter(([key])=>key!=="mode").flatMap(([k,v])=>["--"+k,v])];expect(()=>stage2Authorization([...args,"--resume"],{})).to.throw();expect(()=>stage2Authorization(args.map(x=>x===source?S2.parent:x),{})).to.throw();});
 it("all Stage-2 production files participate in tooling fingerprint",()=>{for(const name of fs.readdirSync(path.resolve(__dirname,"../scripts/galileo")).filter(n=>n.startsWith("recovery2-")&&n.endsWith(".js")))expect(SOURCE_FILES).to.include("scripts/galileo/"+name);});
 for(const [label,transition]of [
  ["state mismatch",f=>f.count=1n],["pending 24/mined 23",f=>f.pending=24],
 ])it("stops if "+label+" appears before signing",()=>scope(async(f,t)=>{const s=await createStage2Store(t);let calls=0,signed=0;await fails(()=>resolveStep24({provider:f.provider,signer:{sendTransaction:async()=>signed++},store:s,bundle:f.bundle,revalidate:async()=>{if(++calls===3)transition(f);return validation(f);},checkPermission(){},maxQuote:S2.maxQuote}));expect(signed).to.equal(0);s.close();}));
 it("MODE A changing to exact MODE B before signing adopts without signing",()=>scope(async(f,t)=>{const s=await createStage2Store(t);let calls=0,signed=0;const revalidate=async()=>{if(++calls===3){f.pending=24;f.mined=24;f.count=1n;f.candidates=[f.candidate];f.balance=BigInt(S2.balance)-f.adoptedReceipt.gasUsed*f.adoptedReceipt.gasPrice;}return validation(f);};const result=await resolveStep24({provider:f.provider,signer:{sendTransaction:async()=>signed++},store:s,bundle:f.bundle,revalidate,checkPermission(){},maxQuote:S2.maxQuote});expect(signed).to.equal(0);expect(result.resolution).to.equal(S2.adoption);s.close();}));
 it("failed first durable save prevents signing",()=>scope(async(f,t)=>{const s=await createStage2Store(t);let signed=0;const original=fs.fsyncSync;fs.fsyncSync=()=>{throw Error("synthetic fsync failure");};try{await fails(()=>resolveStep24({provider:f.provider,signer:{sendTransaction:async()=>signed++},store:s,bundle:f.bundle,revalidate:()=>validation(f),checkPermission(){},maxQuote:S2.maxQuote}));expect(signed).to.equal(0);}finally{fs.fsyncSync=original;s.close();}}));
 it("fake signer can be reached only after durable exact intent; no blind retry",()=>scope(async(f,t)=>{const s=await createStage2Store(t);let signed=0;await fails(()=>resolveStep24({provider:f.provider,signer:{sendTransaction:async request=>{signed++;expect(hash(json(request))).to.equal(S2.requestHash);expect(JSON.parse(fs.readFileSync(t.target)).pendingIntent.requestHash).to.equal(S2.requestHash);throw Error("synthetic one-attempt stop");}},store:s,bundle:f.bundle,revalidate:()=>validation(f),checkPermission(){},maxQuote:S2.maxQuote}));expect(signed).to.equal(1);expect(s.load().pendingIntent.transactionHash).to.equal(undefined);s.close();}));


 for(const trigger of [4,5])it("adopts an exact mined intent at late recheck "+trigger+" without signing",()=>scope(async(f,t)=>{const s=await createStage2Store(t);let calls=0,signed=0;const revalidate=async()=>{if(++calls===trigger){f.pending=24;f.mined=24;f.count=1n;f.candidates=[f.candidate];f.balance=BigInt(S2.balance)-f.adoptedReceipt.gasUsed*f.adoptedReceipt.gasPrice;}return validation(f);};const r=await resolveStep24({provider:f.provider,signer:{sendTransaction:async()=>signed++},store:s,bundle:f.bundle,revalidate,checkPermission(){},maxQuote:S2.maxQuote});expect(signed).to.equal(0);expect(r.resolution).to.equal(S2.adoption);s.close();}));
 it("rejects state drift during the final estimate before any signing",()=>scope(async(f,t)=>{const s=await createStage2Store(t),estimate=f.provider.estimateGas;let estimates=0,signed=0;f.provider.estimateGas=async request=>{if(++estimates===3)f.callOverride=(_,c)=>c.name==="idleBalanceOf"?1n:undefined;return estimate(request);};await fails(()=>resolveStep24({provider:f.provider,signer:{sendTransaction:async()=>signed++},store:s,bundle:f.bundle,revalidate:()=>validation(f),checkPermission(){},maxQuote:S2.maxQuote}));expect(signed).to.equal(0);s.close();}));

 it("Stage-2 permission retains one-attempt raw transport and blocks node-account sends",async()=>{
  const f=H.fixture(),a={...f.authorization,mode:"BROADCAST","approved-source":source};
  const ready=await stage2Readiness({...f,authorization:a});const env={GALILEO_ALLOW_BROADCAST:"YES",GALILEO_USER_APPROVED_SOURCE:source,GALILEO_PRIVATE_KEY:"0x"+"34".repeat(32)};
  const grant=await require("../scripts/galileo/release-boundary").stage2SignerBoundary(ready.readiness,access=>loadPrivateKeySigner(env,{},access,()=>({getAddress:async()=>actor})),a,env,f.recheckSource);
  const {FetchRequest}=require("ethers"),{ExecutionProvider}=require("../scripts/galileo/execution-provider");
  const request=new FetchRequest("https://unit-test.invalid");let attempts=0;request.getUrlFunc=async()=>{attempts++;return {statusCode:429,statusMessage:"synthetic throttle",headers:{},body:new Uint8Array()};};
  const p=new ExecutionProvider(request,{chainId:16602,name:"synthetic"},{staticNetwork:true});
  try{p.enableSubmission(grant.permission);await fails(()=>p._send({id:1,jsonrpc:"2.0",method:"eth_sendTransaction",params:[]}));expect(attempts).to.equal(0);await fails(()=>p._send({id:2,jsonrpc:"2.0",method:"eth_sendRawTransaction",params:["FAKE_NOT_SIGNED"]}));expect(attempts).to.equal(1);}finally{p.destroy();}
 });
 for(const mode of [S2.replay,S2.adopt])it("local full 33-step Stage-2 rehearsal: "+mode,async()=>{
  const local=await H.restoreLocal(),f=H.fixture(mode),t=H.temp(f),base=hre.ethers.provider,offset=S2.block-23,fake=f.provider;
  await hre.network.provider.send("hardhat_setBalance",[actor,"0x"+BigInt(S2.balance).toString(16)]);
  const p={
   send:async(method,args)=>{
    if(method==="eth_chainId")return "0x40da";
    if(method!=="eth_getBlockByNumber")throw Error("only read-only local fixture RPC allowed");
    const number=Number(BigInt(args[0]));if(number<=S2.block)return fake.send(method,args);
    const b=await hre.network.provider.send(method,["0x"+(number-offset).toString(16),args[1]]);return b?{...b,number:"0x"+number.toString(16)}:null;
   },
   getTransaction:async h=>{if(f.transactions.has(h))return structuredClone(f.transactions.get(h));const tx=await base.getTransaction(h);return tx?{...tx,chainId:16602n}:null;},
   getTransactionReceipt:async h=>{if(f.receipts.has(h))return structuredClone(f.receipts.get(h));const r=await base.getTransactionReceipt(h);return r?{...r,logs:r.logs,blockNumber:r.blockNumber+offset}:null;},
   getBlock:async number=>{if(number!=="latest"&&number<=S2.block)return fake.getBlock(number);const b=await base.getBlock(number==="latest"?"latest":number-offset);return b?{...b,number:b.number+offset}:null;},
   getCode:base.getCode.bind(base),getBalance:base.getBalance.bind(base),getTransactionCount:base.getTransactionCount.bind(base),call:base.call.bind(base),estimateGas:base.estimateGas.bind(base),getFeeData:async()=>({gasPrice:4000000007n})
  };
  const localSigner=await hre.ethers.getSigner(actor);let sends=[];
  const signer={getAddress:async()=>actor,sendTransaction:async request=>{
    sends.push(request.nonce);if(request.nonce===23)expect(hash(json(request))).to.equal(S2.requestHash);
    // Test-only chain adapter: all real sends terminate at in-process Hardhat.
    const tx=await localSigner.sendTransaction({...request,chainId:31337});return {hash:tx.hash,wait:async()=>{await tx.wait(1);return p.getTransactionReceipt(tx.hash);}};
  }};
  f.provider=p;t.provider=p;
  if(mode===S2.adopt){
    const historical=await historicalRequest({state:local.state,bundle:local.bundle,review:controlledPlan(),provider:p});await(await signer.sendTransaction(historical.request)).wait(1);sends=[];
  }
  const o=flow(f,t);o.loadSigner=access=>loadPrivateKeySigner(o.env,{},access,()=>signer);
  try{
    const result=await executeStage2(o);expect(result.journal.receipts).to.have.length(33);expect(result.journal.receipts.slice(0,23)).to.deep.equal(f.stage1.receipts);
    expect(sends).to.deep.equal(Array.from({length:mode===S2.adopt?9:10},(_,n)=>n+(mode===S2.adopt?24:23)));
    expect(new Set(result.journal.receipts.map(r=>r.transactionHash)).size).to.equal(33);
    expect(result.journal.reserveWei).to.equal(ORIGINAL.reserveWei);expect(result.journal.maxProjectedSpendWei).to.equal(ORIGINAL.maxProjectedSpendWei);
    if(mode===S2.adopt)expect(result.journal.receipts[23].adoption).to.equal(S2.adoption);
    const last=result.journal.receipts.at(-1);expect(last.readbacks.find(r=>r.label==="vault.idleBalanceOf").value).to.equal("6000000000000");
    expect(last.readbacks.find(r=>r.label==="registration:4:active").value).to.equal(false);
    expect(result.journal.receipts.filter(r=>r.step.startsWith("allocate"))).to.have.length(4);
    expect(t.readEvidence().stage1).to.deep.equal(f.stage1);expect(t.readEvidence().original).to.deep.equal(f.original);
  }finally{fs.rmSync(t.dir,{recursive:true});}
 });
});
