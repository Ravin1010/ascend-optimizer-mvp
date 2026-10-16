"use strict";
const {JsonRpcProvider}=require("ethers");
const {ReadonlyProvider,assertReadonly}=require("./controlled-preview");
const {assertPermission}=require("./release-boundary");
class ExecutionProvider extends ReadonlyProvider {
  #permission=null;
  _getConnection(){const request=super._getConnection();request.setThrottleParams({maxAttempts:1});return request;}
  enableSubmission(permission){assertPermission(permission);this.#permission=permission;}
  async _send(payload){
    const requests=Array.isArray(payload)?payload:[payload];
    const sends=requests.filter(r=>r.method==="eth_sendRawTransaction");
    if(!sends.length){assertReadonly(payload);return super._send(payload);}
    // No eth_sendTransaction/eth_sign/personal_sign is ever permitted, even armed.
    for(const r of requests)if(r.method!=="eth_sendRawTransaction")assertReadonly(r);
    assertPermission(this.#permission);
    return JsonRpcProvider.prototype._send.call(this,payload);
  }
}
module.exports={ExecutionProvider};
