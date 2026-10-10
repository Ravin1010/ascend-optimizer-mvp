import {execFile} from 'node:child_process';
import path from 'node:path';
import {promisify} from 'node:util';
import {NextResponse} from 'next/server.js';
import {parseFinalResponse} from '../../../lib/final-response.ts';
export const runtime='nodejs';
const execute=promisify(execFile);
export async function POST(request:Request) {
 let value:unknown;try {value=await request.json();} catch {return NextResponse.json({error:'Invalid JSON request body'},{status:400});}
 if(!value||typeof value!=='object'||Array.isArray(value)) return NextResponse.json({error:'Request object required'},{status:400});
 const body=value as Record<string,unknown>;
 const profile=body.profile??'Balanced',mode=body.evidence_mode??'PRODUCTION',amount=body.decision_amount_0g,horizon=body.holding_horizon_days??90,deadline=body.cash_deadline_days??null;
 const validNumber=(x:unknown):x is number=>typeof x==='number'&&Number.isFinite(x);
 if(!validNumber(amount)||amount<=0||!validNumber(horizon)||horizon<=0||(deadline!==null&&(!validNumber(deadline)||deadline<0))||(typeof profile!=='string'||!['Conservative','Balanced','Aggressive'].includes(profile))||(typeof mode!=='string'||!['PRODUCTION','SYNTHETIC_EVALUATION_ONLY'].includes(mode))||Object.keys(body).some(k=>!['decision_amount_0g','holding_horizon_days','cash_deadline_days','profile','evidence_mode'].includes(k))) return NextResponse.json({error:'Invalid decision amount, horizon, deadline, profile or evidence mode; existing holdings are outside this request'},{status:400});
 try {const {stdout}=await execute(process.env.PYTHON_BIN??'python',['-m','src.ascend_optimizer.application_contract','--decision-amount-0g',String(amount),'--holding-horizon-days',String(horizon),'--profile',String(profile),'--evidence-mode',String(mode),...(deadline===null?[]:['--cash-deadline-days',String(deadline)])],{cwd:path.resolve(process.cwd(),'..'),timeout:30000,maxBuffer:8*1024*1024});return NextResponse.json(parseFinalResponse(stdout));}
 catch(error) {return NextResponse.json({error:'Optimizer API error',detail:error instanceof Error?error.message:'Execution failed'},{status:500});}
}
