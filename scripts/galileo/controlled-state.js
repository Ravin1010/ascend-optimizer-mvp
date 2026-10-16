"use strict";
const { Contract, keccak256, id, ZeroAddress } = require("ethers");
const { IDS } = require("./plan");
const { stop } = require("./controlled-plan");
function runtimeMatches(code, artifact) {
  if (!code || code === "0x" || !artifact.deployedBytecode || code.length !== artifact.deployedBytecode.length) return false;
  let actual = code.slice(2).toLowerCase(), expected = artifact.deployedBytecode.slice(2).toLowerCase();
  for (const locations of Object.values(artifact.immutableReferences || {})) for (const { start, length } of locations) {
    const mask = "0".repeat(length * 2);
    actual = actual.slice(0,start*2) + mask + actual.slice((start+length)*2);
    expected = expected.slice(0,start*2) + mask + expected.slice((start+length)*2);
  }
  return actual === expected;
}
async function verifyState(provider, bundle, state, completed, actor, config) {
  const done = new Set(completed); const out = [];
  const addr = (a,b) => String(a).toLowerCase() === String(b).toLowerCase();
  const check = (label, actual, expected) => {
    if ((typeof actual === "string" && typeof expected === "string" && expected.startsWith("0x")) ? !addr(actual,expected) : actual !== expected) stop(`incorrect ownership/configuration/readback: ${label}`);
    out.push({label,value:typeof actual === "bigint" ? actual.toString() : actual});
  };
  const read = async (name, method, args, expected) => {
    const c = new Contract(state[name], bundle[state.artifactNames[name]].abi, provider);
    const value = await c[method](...(args || [])); check(`${name}.${method}`,value,expected); return value;
  };
  for (const [name, artifactName] of Object.entries(state.artifactNames)) {
    const code = await provider.getCode(state[name]);
    if (!runtimeMatches(code,bundle[artifactName]) || keccak256(code) !== state.codeHashes[name]) stop(`incorrect deployed bytecode: ${name}`);
  }
  if (state.manager) {
    await read("manager","owner",[],actor);
    const regs = [...done].filter(n=>/^register[0-4]$/.test(n));
    await read("manager","strategyCount",[],BigInt(regs.length));
    const m = new Contract(state.manager,bundle.StrategyManager.abi,provider);
    const names=["nativeAdapter","gimoAdapter","jaineAdapter","okuAdapter","ascendAdapter"];
    for (let i=0;i<5;i++) if(done.has(`register${i}`)) {
      check(`strategyIdAt:${i}`,await m.strategyIdAt(i),id(IDS[i]));
      const r=await m.getStrategy(id(IDS[i]));
      for(const [k,v] of Object.entries({adapter:state[names[i]],inputAsset:ZeroAddress,depositCap:BigInt(config.depositCapWei),maxAllocationBps:5000n,asynchronous:[0,1,4].includes(i),active:i!==4})) check(`registration:${i}:${k}`,r[k],v);
    }
    check("Ascend inactive",await m.isStrategyActive(id(IDS[4])),false);
  }
  if(state.vault) {
    await read("vault","owner",[],actor); await read("vault","strategyManager",[],state.manager);
    await read("vault","rewardAccounting",[],ZeroAddress); await read("vault","paused",[],false);
    const allocations=[0,1,2,3].filter(i=>done.has(`allocate${i}`));
    await read("vault","idleBalanceOf",[actor,ZeroAddress],done.has("deposit") ? BigInt(config.depositWei)-BigInt(allocations.length)*BigInt(config.allocationWei) : 0n);
    for(let i=0;i<5;i++) await read("vault","strategySharesOf",[actor,id(IDS[i])],allocations.includes(i) ? BigInt(i<2 ? config.stakingMinShares:config.v3MinLiquidity):0n);
  }
  if(state.nativeAdapter) { await read("nativeAdapter","owner",[],actor); await read("nativeAdapter","vault",[],state.vault); await read("nativeAdapter","validator",[],state.validator); }
  if(state.validator) { await read("validator","withdrawalFeeInGwei",[],1n); await read("validator","totalDelegated",[],done.has("allocate0")?BigInt(config.allocationWei):0n); }
  if(state.gimoPool) await read("gimoPool","st0g",[],state.gimoToken);
  if(state.gimoToken) { await read("gimoToken","minter",[],state.gimoPool); await read("gimoToken","getRate",[],10n**18n); }
  if(state.gimoAdapter) {
    for(const [k,v] of Object.entries({vault:state.vault,stakePool:state.gimoPool,st0g:state.gimoToken})) await read("gimoAdapter",k,[],v);
    await read("gimoAdapter","referral",[],"ascend-galileo-validation");
  }
  if(state.factory) await read("factory","pool",[],done.has("setPool")?state.pool:ZeroAddress);
  if(state.pool) for(const [k,v] of Object.entries({factory:state.factory,token0:state.w0g,token1:state.usdce,fee:3000n,tickSpacing:60n})) await read("pool",k,[],v);
  for(const name of ["npm","v1","r02"]) if(state[name]) await read(name,"factory",[],state.factory);
  if(state.usdce) for(const [router,seed,allocation] of [["v1","seedV1","allocate2"],["r02","seedR02","allocate3"]]) if(state[router]) await read("usdce","balanceOf",[state[router]],done.has(seed)?BigInt(config.routerFundingRaw)-(done.has(allocation)?BigInt(config.allocationWei)/2n:0n):0n);
  for(const [name,router,mode,allocation,token] of [["jaineAdapter","v1",0n,"allocate2",1n],["okuAdapter","r02",1n,"allocate3",2n]]) if(state[name]) {
    for(const [k,v] of Object.entries({vault:state.vault,factory:state.factory,router:state[router],positionManager:state.npm,pool:state.pool,w0g:state.w0g,usdce:state.usdce,feeTier:3000n,tickLower:-600n,tickUpper:600n,sqrtLowerX96:2n**95n,sqrtUpperX96:2n**97n,targetUsdcBps:5000n,routerMode:mode})) await read(name,k,[],v);
    await read(name,"tokenId",[],done.has(allocation)?token:0n);
    await read(name,"totalStrategyShares",[],done.has(allocation)?BigInt(config.v3MinLiquidity):0n);
  }
  if(state.sourceCore) { await read("sourceCore","asset",[],state.ascendW0g); await read("sourceCore","withdrawalQueue",[],done.has("attachQueue")?state.queue:ZeroAddress); await read("sourceCore","rate",[],10n**18n); }
  if(state.queue) { await read("queue","asset",[],state.ascendW0g); await read("queue","sourceCore",[],state.sourceCore); }
  if(state.ascendAdapter) for(const [k,v] of Object.entries({vault:state.vault,sourceCore:state.sourceCore,w0g:state.ascendW0g,withdrawalQueue:state.queue})) await read("ascendAdapter",k,[],v);
  return out;
}
module.exports={runtimeMatches,verifyState};
