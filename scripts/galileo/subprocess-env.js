"use strict";
// Explicit allowlist: never enumerate the environment or read signing credentials.
function sanitizedChildEnv(env=process.env) {
  const child={};
  for(const name of ["PATH","SystemRoot","WINDIR","PATHEXT","LANG","LC_ALL","TZ"]){
    if(typeof env[name]==="string")child[name]=env[name];
  }
  return child;
}
module.exports={sanitizedChildEnv};
