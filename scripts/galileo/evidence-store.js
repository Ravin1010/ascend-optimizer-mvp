"use strict";
const fs = require("node:fs");
const path = require("node:path");
// Single-writer, atomic receipt journal. A durable pending intent is never replayed.
// Keep journals under ignored galileo-local/; no secrets or raw error messages.
function evidenceStore(file, resume = false) {
  fs.mkdirSync(path.dirname(file), {recursive:true});
  const lock = file + ".lock";
  const fd = fs.openSync(lock, "wx", 0o600);
  try {
    if (fs.existsSync(file) !== resume) throw new Error("STOP: evidence exists/resume mismatch");
    return {
      load: () => resume ? JSON.parse(fs.readFileSync(file, "utf8")) : null,
      save(value) {
        const tmp = file + ".tmp";
        const pending=fs.openSync(tmp,"wx",0o600);
        try {fs.writeFileSync(pending,JSON.stringify(value,(_,v)=>typeof v === "bigint"?v.toString():v,2)+"\n");fs.fsyncSync(pending);} finally {fs.closeSync(pending);}
        fs.renameSync(tmp,file);
        const directory=fs.openSync(path.dirname(file),"r");
        try {fs.fsyncSync(directory);} finally {fs.closeSync(directory);}
      },
      close() { fs.closeSync(fd); fs.unlinkSync(lock); }
    };
  } catch (error) { fs.closeSync(fd); fs.unlinkSync(lock); throw error; }
}
module.exports = { evidenceStore };
