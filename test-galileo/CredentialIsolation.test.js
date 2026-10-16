"use strict";
const {expect}=require("chai");
const {fixture,source,actor}=require("./ReleaseReview.test");
const {readinessChecks}=require("../scripts/galileo/release-review");
const {futureSignerBoundary,loadPrivateKeySigner,assertPermission}=require("../scripts/galileo/release-boundary");
const {sanitizedChildEnv}=require("../scripts/galileo/subprocess-env");
const synthetic="0x"+"b".repeat(64);
function approval(){return {GALILEO_ALLOW_BROADCAST:"YES",GALILEO_USER_APPROVED_SOURCE:source};}
async function fails(fn){let error;try{await fn();}catch(e){error=e;}expect(error).to.be.instanceOf(Error);expect(error.message).not.to.include(synthetic);return error;}
describe("Post-signer credential and subprocess isolation",function(){
 it("consumes a credential getter once, removes it, and preserves repeated approvals and usable signer",async()=>{
  const f=fixture(),r=await readinessChecks(f),e=approval();let reads=0,calls=0;
  Object.defineProperty(e,"GALILEO_PRIVATE_KEY",{configurable:true,get(){reads++;return synthetic;}});
  const signer={getAddress:async()=>actor,syntheticOperation:()=>++calls};
  const grant=await futureSignerBoundary(r,access=>loadPrivateKeySigner(e,{},access,()=>signer),f.authorization,e,f.recheckSource);
  expect(reads).to.equal(1);expect("GALILEO_PRIVATE_KEY" in e).to.equal(false);
  expect(e.GALILEO_ALLOW_BROADCAST).to.equal("YES");expect(e.GALILEO_USER_APPROVED_SOURCE).to.equal(source);
  for(let i=0;i<3;i++){assertPermission(grant.permission);expect(grant.signer.syntheticOperation()).to.equal(i+1);}
  expect(reads).to.equal(1);expect(JSON.stringify(grant.permission)).not.to.include(synthetic);
 });
 it("sanitized child environment never reads a credential getter or enumerates environment",()=>{
  const input=new Proxy({PATH:process.env.PATH,GALILEO_ALLOW_BROADCAST:"YES"},{get(t,k){if(k==="GALILEO_PRIVATE_KEY")throw Error("secret getter");return t[k];},ownKeys(){throw Error("enumeration forbidden");}});
  expect(sanitizedChildEnv(input)).to.deep.equal({PATH:process.env.PATH});
 });
 it("actual child process receives no synthetic credential",()=>{
  const {execFileSync}=require("node:child_process");
  const result=execFileSync(process.execPath,["-e","if('GALILEO_PRIVATE_KEY' in process.env)process.exit(19);process.stdout.write('isolated')"],{env:sanitizedChildEnv({PATH:process.env.PATH,GALILEO_PRIVATE_KEY:synthetic}),encoding:"utf8"});
  expect(result).to.equal("isolated");
 });
 it("every Git sourceState invocation explicitly isolates the environment, including repeated post-signer checks",async()=>{
  const child=require("node:child_process"),original=child.execFileSync,modulePath=require.resolve("../scripts/galileo/release-integrity"),cached=require.cache[modulePath];let gitCalls=0;
  try{
   child.execFileSync=(command,args,options)=>{expect(command).to.equal("git");expect(options).to.have.property("env");expect(options.env).not.to.have.property("GALILEO_PRIVATE_KEY");gitCalls++;return args[0]==="rev-parse"?source:args[0]==="branch"?"feature/galileo-deployment-tooling":"";};
   delete require.cache[modulePath];const {sourceState}=require(modulePath);
   const f=fixture(),r=await readinessChecks(f),e={...approval(),GALILEO_PRIVATE_KEY:synthetic};
   const grant=await futureSignerBoundary(r,access=>loadPrivateKeySigner(e,{},access,()=>({getAddress:async()=>actor})),f.authorization,e,()=>({...sourceState(),tooling:f.integrity.state.tooling}));
   for(let i=0;i<3;i++)assertPermission(grant.permission);
   expect(gitCalls).to.be.at.least(20);expect("GALILEO_PRIVATE_KEY" in e).to.equal(false);
  }finally{child.execFileSync=original;delete require.cache[modulePath];if(cached)require.cache[modulePath]=cached;}
 });
 for(const kind of ["nonconfigurable","inherited","deletion rejected"]){
  it("fails closed on credential cleanup: "+kind,async()=>{
   const f=fixture(),r=await readinessChecks(f);let e=approval();
   if(kind==="nonconfigurable")Object.defineProperty(e,"GALILEO_PRIVATE_KEY",{value:synthetic,configurable:false});
   else if(kind==="inherited")Object.setPrototypeOf(e,{GALILEO_PRIVATE_KEY:synthetic});
   else e=new Proxy({...e,GALILEO_PRIVATE_KEY:synthetic},{deleteProperty(){return false;}});
   await fails(()=>futureSignerBoundary(r,access=>loadPrivateKeySigner(e,{},access,()=>({getAddress:async()=>actor})),f.authorization,e,f.recheckSource));
  });
 }
 it("rejects an injected loader that leaves the credential present",async()=>{const f=fixture(),r=await readinessChecks(f),e={...approval(),GALILEO_PRIVATE_KEY:synthetic};await fails(()=>futureSignerBoundary(r,async()=>({getAddress:async()=>actor}),f.authorization,e,f.recheckSource));});
 it("revokes permission if a credential is reintroduced after cleanup",async()=>{const f=fixture(),r=await readinessChecks(f),e={...approval(),GALILEO_PRIVATE_KEY:synthetic};const g=await futureSignerBoundary(r,a=>loadPrivateKeySigner(e,{},a,()=>({getAddress:async()=>actor})),f.authorization,e,f.recheckSource);e.GALILEO_PRIVATE_KEY=synthetic;expect(()=>assertPermission(g.permission)).to.throw("isolation failed");});
 for(const value of [undefined,"invalid-synthetic",synthetic])it("cleans failed/missing/malformed construction without leaking errors: "+String(value===synthetic?"constructor":value),async()=>{const f=fixture(),r=await readinessChecks(f),e={...approval(),GALILEO_PRIVATE_KEY:value};await fails(()=>futureSignerBoundary(r,a=>loadPrivateKeySigner(e,{},a,()=>{throw Error(synthetic);}),f.authorization,e,f.recheckSource));expect("GALILEO_PRIVATE_KEY" in e).to.equal(false);});
 it("cleans before signer-address mismatch and never creates permission",async()=>{const f=fixture(),r=await readinessChecks(f),e={...approval(),GALILEO_PRIVATE_KEY:synthetic};await fails(()=>futureSignerBoundary(r,a=>loadPrivateKeySigner(e,{},a,()=>({getAddress:async()=>"0x0000000000000000000000000000000000000001"})),f.authorization,e,f.recheckSource));expect("GALILEO_PRIVATE_KEY" in e).to.equal(false);});
 it("cleans a throwing getter and sanitizes its error",async()=>{const f=fixture(),r=await readinessChecks(f),e=approval();let reads=0;Object.defineProperty(e,"GALILEO_PRIVATE_KEY",{configurable:true,get(){reads++;throw Error(synthetic);}});await fails(()=>futureSignerBoundary(r,a=>loadPrivateKeySigner(e,{},a),f.authorization,e,f.recheckSource));expect(reads).to.equal(1);expect("GALILEO_PRIVATE_KEY" in e).to.equal(false);});
 it("provider arming and engine evidence occur only after cleanup and contain no credential",async()=>{
  const {executeRelease}=require("../scripts/galileo/release-review"),f=fixture(),e={...approval(),GALILEO_PRIVATE_KEY:synthetic};let armed=0,read=0;
  const result=await executeRelease({...f,env:e,store:{load:()=>null},loadSigner:a=>loadPrivateKeySigner(e,{},a,()=>({getAddress:async()=>actor})),armProvider:p=>{expect("GALILEO_PRIVATE_KEY" in e).to.equal(false);assertPermission(p);armed++;},runEngine:async options=>{read++;assertPermission(options.permission);expect("env" in options).to.equal(false);return {journal:{publicEvidenceOnly:true,source:options.sourceCommit}};}});
  expect(armed).to.equal(1);expect(read).to.equal(1);expect(JSON.stringify(result)).not.to.include(synthetic);
 });

});
