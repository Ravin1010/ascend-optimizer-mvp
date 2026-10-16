"use strict";
const {sanitizedChildEnv}=require("./subprocess-env");
const hre=require("hardhat");
const path=require("node:path");
const {execFileSync}=require("node:child_process");
const {runLocal}=require("./controlled-executor");
const {evidenceStore}=require("./evidence-store");
async function main() {
  // No public execution option exists. In-process Hardhat only, before any signer.
  if(hre.network.name !== "hardhat") throw Error("STOP: local rehearsal only");
  const file=path.resolve("galileo-local/controlled-local.json");
  const store=evidenceStore(file);
  try {
    const sourceCommit=execFileSync("git",["rev-parse","HEAD"],{env:sanitizedChildEnv(),encoding:"utf8"}).trim();
    const {journal,state}=await runLocal({hre,sourceCommit,store});
    console.log(JSON.stringify({mode:journal.mode,localTransactions:journal.receipts.length,publicTransactionsSubmitted:0,ascendActive:false,expectedIdleWei:"6000000000000",cumulativeSpendWei:journal.cumulativeSpendWei,localVault:state.vault,evidence:file},null,2));
  } finally {store.close();}
}
if(require.main===module) main().catch(()=>{console.error("STOP: local rehearsal failed; inspect non-secret receipt journal. Public submission remains sealed.");process.exitCode=1;});
module.exports={main};
