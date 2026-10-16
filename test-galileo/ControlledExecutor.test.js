const {expect}=require("chai");
const hre=require("hardhat");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const {controlledPlan,reviewed}=require("../scripts/galileo/controlled-plan");
const {runLocal,publicExecution,publicPreview,context,guardTransaction,budgetGuard,validateResume,artifactsFor}=require("../scripts/galileo/controlled-executor");
const {runtimeMatches,verifyState}=require("../scripts/galileo/controlled-state");
const {evidenceStore}=require("../scripts/galileo/evidence-store");
const {assertReadonly}=require("../scripts/galileo/controlled-preview");
const {readonlyRpc}=require("../scripts/galileo/preflight");
const clone=x=>JSON.parse(JSON.stringify(x));
const actor=reviewed.deployer;
function memory() {let value=null;return {load:()=>clone(value),save:x=>{value=clone(x);},get:()=>clone(value)};}
async function rejects(fn,text) {let e;try {await fn();}catch(error){e=error;}expect(e?.message).to.include(text);}
function guards(overrides={}) {
 const provider={send:async()=>"0x40da",getBalance:async()=>10000n,getTransactionCount:async()=>0,getBlock:async()=>({timestamp:100}),getFeeData:async()=>({gasPrice:1n}),estimateGas:async()=>100n,...overrides};
 return {provider,actor,expectedActor:actor,expectedChain:16602,nonce:0,request:{from:actor,nonce:0,value:0n},step:{referenceGas:100},steps:[{referenceGas:100}],index:0,config:reviewed,journal:{initialBalanceWei:"10000",reserveWei:"2000",cumulativeSpendWei:"0",feeCeilingWei:"2"}};
}
describe("Controlled Galileo executor — sealed public boundary",function(){
 this.timeout(120000);
 it("freezes reviewed values and the 33 transaction graph",function(){const p=controlledPlan();expect(p.transactionSteps).to.have.length(33);expect(p.plan.counts).to.deep.equal({DEPLOY:19,CONFIGURE:9,INTERACT:5});expect(p.config.depositWei).to.equal("10000000000000");expect(p.config.expectedIdleWei).to.equal("6000000000000");});
 for(const field of ["native","gimo","jaine","oku","ascend"]) it(`rejects ${field} branch drift`,function(){expect(()=>controlledPlan({...reviewed,[field]:"LIVE"})).to.throw("drift");});
 it("rejects altered funding/minimum/caps and unknown fields",function(){for(const field of ["depositWei","stakingMinShares","v3MinLiquidity","maxAllocationBps","depositCapWei"])expect(()=>controlledPlan({...reviewed,[field]:"1"})).to.throw("drift");expect(()=>controlledPlan({...reviewed,secret:"not logged"})).to.throw("unknown");});
 it("rejects weakened reserve/gas safety settings",function(){for(const field of ["reserveBps","gasMarginBps","feeMultiplierBps"])expect(()=>controlledPlan({...reviewed,[field]:0})).to.throw("safety policy");});
 it("rejects wrong chain",async()=>rejects(()=>guardTransaction(guards({send:async()=>"0x1"})),"wrong chain"));
 it("rejects wrong deployer",async()=>rejects(()=>context({},16602,actor,hre.ethers.ZeroAddress),"wrong deployer"));
 it("rejects insufficient balance",async()=>rejects(()=>guardTransaction(guards({getBalance:async()=>1n})),"insufficient balance"));
 it("rejects reserve breach",async()=>rejects(()=>guardTransaction(guards({getBalance:async()=>2100n})),"reserve breach"));
 it("rejects failed public estimation with no local substitute",async()=>rejects(()=>guardTransaction(guards({estimateGas:async()=>{throw Error("rpc failure");}})),"gas estimate failure"));
 it("rejects gas estimate beyond reviewed funding envelope",async()=>{const g=guards({estimateGas:async()=>200n});g.journal.maxProjectedSpendWei="300";await rejects(()=>guardTransaction(g),"materially exceeds");});
 it("rejects fee spike",async()=>rejects(()=>guardTransaction(guards({getFeeData:async()=>({gasPrice:3n})})),"fee spike"));
 it("rejects missing fee quote",async()=>rejects(()=>guardTransaction(guards({getFeeData:async()=>({gasPrice:null})})),"fee quote unavailable"));
 it("rejects nonce mismatch",async()=>rejects(()=>guardTransaction(guards({getTransactionCount:async()=>1})),"nonce mismatch"));
 it("rejects stale deadline",async()=>{const g=guards();g.request.deadline=120n;await rejects(()=>guardTransaction(g),"stale deadline");});
 it("strips deadline metadata and uses a fresh successful estimate",async()=>{let called=false;const g=guards({estimateGas:async tx=>{expect(tx).not.to.have.property("deadline");called=true;return 100n;}});g.request.deadline=3700n;const r=await guardTransaction(g);expect(r.gasLimit).to.equal(120n);expect(called).to.equal(true);});
 it("protects cumulative initial balance even with later funding",()=>expect(()=>budgetGuard({balance:10000n,initialBalance:1000n,reserve:200n,spent:750n,remaining:100n})).to.throw("reserve breach"));
 it("public execution gate always rejects before reading arguments or secrets",()=>{const trap=new Proxy({}, {get(){throw Error("must not inspect");}});expect(()=>publicExecution(trap)).to.throw("disabled");});
 for(const method of ["eth_sendRawTransaction","eth_sendTransaction","eth_sign","eth_signTransaction","personal_sign"]) it(`public read-only transport blocks ${method}`,async()=>{let touched=false;await rejects(()=>readonlyRpc({send(){touched=true;}})(method,[]),"forbidden");expect(touched).to.equal(false);});
 it("rejects public chain before local signer creation",async()=>{const fake={network:{name:"galileo"},ethers:{getSigners(){throw Error("signer accessed");}}};await rejects(()=>runLocal({hre:fake}),"in-process Hardhat");});
 it("public preview is unsigned and balance-aware",async()=>{const p=guards().provider;p.getBalance=async()=>hre.ethers.parseEther("0.61");p.getBlock=async()=>({number:1,hash:"0x1",timestamp:100});const r=await publicPreview(p);expect(r.transactionsSubmitted).to.equal(0);expect(r.reserveWei).to.equal("122000000000000000");expect(r.broadcastReady).to.equal(false);});
 it("rejects forbidden public RPC batches before transport",()=>{expect(()=>assertReadonly([{method:"eth_chainId"},{method:"eth_sendRawTransaction"}])).to.throw("forbidden");expect(()=>assertReadonly({method:"eth_getTransactionCount"})).not.to.throw();});
 it("rejects cumulative material envelope growth",async()=>{const g=guards();g.journal.maxProjectedSpendWei="100";await rejects(()=>guardTransaction(g),"materially exceeds");});
 it("journal uses exclusive writer lock and refuses overwrite",()=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),"galileo-journal-"));const file=path.join(dir,"journal.json");const s=evidenceStore(file);s.save({receipts:[],pendingIntent:null});expect(()=>evidenceStore(file)).to.throw();s.close();expect(()=>evidenceStore(file)).to.throw("mismatch");const r=evidenceStore(file,true);expect(r.load().receipts).to.deep.equal([]);r.close();fs.rmSync(dir,{recursive:true});});
 let result,store,bundle,review,actorLocal;
 it("executes all 33 steps locally with receipt evidence and exact idle",async()=>{
   await hre.network.provider.send("hardhat_reset");store=memory();review=controlledPlan();
   result=await runLocal({hre,store,sourceCommit:"local-test-source"});
   bundle=await artifactsFor(hre,review.plan);actorLocal=result.journal.actor;
   expect(result.journal.receipts).to.have.length(33);
   const names=result.journal.receipts.map(r=>r.step);expect(names).to.deep.equal(review.transactionSteps.map(s=>s.name));
   expect(names.filter(n=>n.startsWith("allocate"))).to.have.length(4);
   expect(result.journal.mode).to.equal("LOCAL_ONLY");expect(result.journal.pendingIntent).to.equal(null);
   for(const r of result.journal.receipts){expect(r.status).to.equal("CONFIRMED");expect(BigInt(r.gasUsed)).to.be.gt(0n);expect(r.blockHash).to.match(/^0x/);expect(r.readbacks.length).to.be.gt(0);expect(r.localEvidenceOnly).to.equal(true);expect(r.explorerLink).to.equal(null);}
   expect(result.journal.receipts.at(-1).readbacks.find(r=>r.label==="vault.idleBalanceOf").value).to.equal("6000000000000");
 });
 const resumeArgs=()=>({provider:hre.ethers.provider,bundle,review,sourceCommit:"local-test-source",journal:clone(result.journal),actor:actorLocal,expectedChain:31337});
 it("resumes completed graph without duplicate transactions",async()=>{const before=await hre.ethers.provider.getTransactionCount(actorLocal);await runLocal({hre,store,sourceCommit:"local-test-source"});expect(await hre.ethers.provider.getTransactionCount(actorLocal)).to.equal(before);});
 it("rejects wrong resume source/config/artifacts",async()=>{for(const key of ["sourceCommit","planHash","artifactHash"]){const a=resumeArgs();a.journal[key]="bad";await rejects(()=>validateResume(a),"configuration mismatch");}});
 it("rejects altered resume reserve/envelope",async()=>{for(const key of ["reserveWei","maxProjectedSpendWei"]){const a=resumeArgs();a.journal[key]="0";await rejects(()=>validateResume(a),key==="reserveWei"?"policy mismatch":"envelope mismatch");}});
 it("rejects altered receipt argument evidence",async()=>{const a=resumeArgs();a.journal.receipts[0].arguments=[];await rejects(()=>validateResume(a),"argument evidence mismatch");});
 it("rejects durable pending intent instead of duplicate execution",async()=>{const a=resumeArgs();a.journal.pendingIntent={step:"manager"};await rejects(()=>validateResume(a),"ambiguous");});
 it("rejects duplicate/misordered step",async()=>{const a=resumeArgs();a.journal.receipts[0].step="vault";await rejects(()=>validateResume(a),"duplicate-step");});
 it("rejects failed receipt evidence",async()=>{const a=resumeArgs();a.journal.receipts[0].status="FAILED";await rejects(()=>validateResume(a),"history mismatch");});
 it("rejects missing/failed on-chain receipt",async()=>{const a=resumeArgs();a.provider=new Proxy(a.provider,{get(t,p){if(p==="getTransactionReceipt")return async()=>({status:0});const v=t[p];return typeof v==="function"?v.bind(t):v;}});await rejects(()=>validateResume(a),"failed/missing");});
 it("rejects changed transaction calldata",async()=>{const a=resumeArgs();const provider=a.provider;a.provider=new Proxy(provider,{get(t,p){if(p==="getTransaction")return async h=>({...await t.getTransaction(h),data:"0x00"});const v=t[p];return typeof v==="function"?v.bind(t):v;}});await rejects(()=>validateResume(a),"calldata mismatch");});
 it("rejects changed cost evidence",async()=>{const a=resumeArgs();a.journal.receipts[0].gasCostWei="0";await rejects(()=>validateResume(a),"cost mismatch");});
 it("rejects incorrect deployed bytecode",async()=>{const a=resumeArgs();const snap=await hre.network.provider.send("evm_snapshot");await hre.network.provider.send("hardhat_setCode",[result.state.nativeAdapter,"0x6000"]);await rejects(()=>validateResume(a),"incorrect deployed bytecode");await hre.network.provider.send("evm_revert",[snap]);});
 it("rejects accidental Ascend activation",async()=>{const snap=await hre.network.provider.send("evm_snapshot");const [owner]=await hre.ethers.getSigners();const m=new hre.ethers.Contract(result.state.manager,bundle.StrategyManager.abi,owner);await(await m.updateLimits(hre.ethers.id("ASCEND_STAKE_A0G"),10n**15n,5000,true)).wait();await rejects(()=>verifyState(hre.ethers.provider,bundle,result.state,result.journal.receipts.map(r=>r.step),actorLocal,review.config),"registration:4:active");await hre.network.provider.send("evm_revert",[snap]);});
 it("rejects wrong ownership/configuration",async()=>{const snap=await hre.network.provider.send("evm_snapshot");const [owner,other]=await hre.ethers.getSigners();const m=new hre.ethers.Contract(result.state.manager,bundle.StrategyManager.abi,owner);await(await m.transferOwnership(other.address)).wait();await(await m.connect(other).acceptOwnership()).wait();await rejects(()=>verifyState(hre.ethers.provider,bundle,result.state,result.journal.receipts.map(r=>r.step),actorLocal,review.config),"manager.owner");await hre.network.provider.send("evm_revert",[snap]);});
 it("rejects unrelated nonce changes on resume",async()=>{const snap=await hre.network.provider.send("evm_snapshot");const [owner]=await hre.ethers.getSigners();await(await owner.sendTransaction({to:actorLocal,value:0})).wait();await rejects(()=>validateResume(resumeArgs()),"nonce mismatch");await hre.network.provider.send("evm_revert",[snap]);});
 it("resumes a confirmed prefix and only sends remaining steps",async()=>{await hre.network.provider.send("hardhat_reset");const s=memory();let r=await runLocal({hre,store:s,sourceCommit:"prefix-test",maxSteps:5});expect(r.journal.receipts.length).to.equal(5);r=await runLocal({hre,store:s,sourceCommit:"prefix-test"});expect(r.journal.receipts.length).to.equal(33);expect(new Set(r.journal.receipts.map(r=>r.transactionHash)).size).to.equal(33);});
});
