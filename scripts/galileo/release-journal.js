"use strict";
const fs=require("node:fs"),path=require("node:path");
const {evidenceStore}=require("./evidence-store");
const {stop}=require("./controlled-plan");
const ROOT=path.resolve(__dirname,"../.."),BASE=path.join(ROOT,"galileo-local");
function releaseStore(authorization,readOnly=false){
  const file=path.resolve(ROOT,authorization.journal||"galileo-local/final-galileo-receipts.json");
  const rel=path.relative(BASE,file);
  if(!rel||rel.startsWith("..")||path.isAbsolute(rel)||!file.endsWith(".json"))stop("journal must be an isolated galileo-local JSON file");
  for(let p=file;p!==ROOT;p=path.dirname(p))if(fs.existsSync(p)&&fs.lstatSync(p).isSymbolicLink())stop("journal symlink forbidden");
  if(readOnly){
    if(fs.existsSync(file)!==Boolean(authorization.resume))stop("journal exists/resume mismatch");
    return {load:()=>authorization.resume?JSON.parse(fs.readFileSync(file,"utf8")):null,close(){}};
  }
  return evidenceStore(file,Boolean(authorization.resume));
}
module.exports={releaseStore};
