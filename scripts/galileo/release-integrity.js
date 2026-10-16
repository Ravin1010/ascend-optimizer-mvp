"use strict";
const fs=require("node:fs"),path=require("node:path");
const {execFileSync}=require("node:child_process");
const {controlledPlan,stop}=require("./controlled-plan");
const {hash}=require("./plan");
const ROOT=path.resolve(__dirname,"../..");
const SOURCE_FILES=["hardhat.config.js","hardhat.galileo.config.js","package.json","package-lock.json",...[
  "controlled-executor.js","controlled-plan.js","controlled-state.js","controlled-preview.js","plan.js","preflight.js","evidence-store.js","reviewed-execution.json","release-policy.js","release-integrity.js","release-review.js","release-boundary.js","release-run.js"
].map(f=>"scripts/galileo/"+f)];
function sourceState() {
  const git=(...args)=>execFileSync("git",args,{cwd:ROOT,encoding:"utf8",stdio:["ignore","pipe","pipe"]}).trim();
  const source=git("rev-parse","HEAD"),branch=git("branch","--show-current");
  const clean=!git("status","--porcelain");
  let lineage=true;try{git("merge-base","--is-ancestor","c2a48978e5d7baa1806a75fc0444a71bf8875afd","HEAD");}catch{lineage=false;}
  return {source,branch,clean,lineage,tooling:hash(SOURCE_FILES.map(f=>({path:f,content:fs.readFileSync(path.join(ROOT,f),"utf8")})))};
}
function loadArtifacts() {
  const review=controlledPlan();
  const names=[...new Set(review.plan.steps.filter(s=>s.kind === "DEPLOY").map(s=>s.contract).concat("MockGimoSt0G"))];
  const candidates=[];
  function walk(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,entry.name);if(entry.isDirectory())walk(p);else if(p.endsWith(".json")&&!p.endsWith(".dbg.json"))candidates.push(p);}}
  walk(path.join(ROOT,"artifacts-galileo/contracts"));
  const bundle={};
  for(const name of names){
    const matches=candidates.filter(p=>path.basename(p) === name+".json");if(matches.length !== 1)stop("missing/ambiguous release artifact");
    const file=matches[0],a=JSON.parse(fs.readFileSync(file,"utf8"));
    const dbg=JSON.parse(fs.readFileSync(file.replace(/\.json$/,".dbg.json"),"utf8"));
    const buildPath=path.resolve(path.dirname(file),dbg.buildInfo);
    if(!buildPath.startsWith(path.join(ROOT,"artifacts-galileo/build-info")+path.sep)||!/^[0-9a-f]+\.json$/.test(path.basename(buildPath)))stop("unexpected build-info path");
    const build=JSON.parse(fs.readFileSync(buildPath,"utf8"));
    const settings=build.input.settings;
    if(build.solcVersion !== "0.8.24" || settings.evmVersion !== "cancun" || settings.optimizer?.enabled !== true || settings.optimizer.runs !== 200 || Object.keys(a.linkReferences).length || Object.keys(a.deployedLinkReferences).length)stop("release build/link mismatch");
    for(const [source,input] of Object.entries(build.input.sources)){
      if(path.posix.normalize(source)!==source || source.includes("..") || (!source.startsWith("contracts/")&&!source.startsWith("@openzeppelin/contracts/")))stop("unexpected compiler source");
      const current=fs.readFileSync(path.join(ROOT,source.startsWith("@")?"node_modules":"",source),"utf8");
      if(current !== input.content)stop("stale compiler source/artifact");
    }
    const output=build.output.contracts[a.sourceName][name];
    if(a.bytecode !== "0x"+output.evm.bytecode.object || a.deployedBytecode !== "0x"+output.evm.deployedBytecode.object || hash(a.abi)!==hash(output.abi))stop("artifact/build output mismatch");
    bundle[name]={abi:a.abi,bytecode:a.bytecode,deployedBytecode:a.deployedBytecode,immutableReferences:output.evm.deployedBytecode.immutableReferences};
  }
  return bundle;
}
function identity() {
  const state=sourceState(),bundle=loadArtifacts();
  return {state,bundle,artifactHash:hash(bundle),planHash:controlledPlan().fingerprint};
}
module.exports={sourceState,loadArtifacts,identity,SOURCE_FILES};
