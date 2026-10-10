import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync,readdirSync} from 'node:fs';
import {test} from 'node:test';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import ts from 'typescript';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {POST} from '../src/app/api/decision-sleeve/route.ts';
import {parseFinalResponse,displayMeasurement,deadlineLabel} from '../src/lib/final-response.ts';
import {STRATEGY_IDS} from '../src/lib/final-types.ts';
import type {FinalResponse} from '../src/lib/final-types.ts';

const root=path.resolve(process.cwd(),'..');
function result(mode:string,extra:string[]=[]):FinalResponse {return parseFinalResponse(execFileSync(process.env.PYTHON_BIN??'python',['-m','src.ascend_optimizer.application_contract','--decision-amount-0g','1000','--evidence-mode',mode,...extra],{cwd:root,encoding:'utf8'}));}
const prod=result('PRODUCTION'),synthetic=result('SYNTHETIC_EVALUATION_ONLY'),tight=result('SYNTHETIC_EVALUATION_ONLY',['--cash-deadline-days','1']);
const compiled=ts.transpileModule(readFileSync('src/app/decision-view.tsx','utf8'),{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText
 .replace('../lib/final-response.ts',pathToFileURL(path.resolve('src/lib/final-response.ts')).href)
 .replace('react/jsx-runtime',pathToFileURL(path.resolve('node_modules/react/jsx-runtime.js')).href);
const {DecisionView}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64')) as {DecisionView:React.ComponentType<{data:FinalResponse}>};
const html=renderToStaticMarkup(React.createElement(DecisionView,{data:synthetic}));
const idleHtml=renderToStaticMarkup(React.createElement(DecisionView,{data:prod}));
const page=readFileSync('src/app/page.tsx','utf8'),css=readFileSync('src/app/globals.css','utf8');
function request(body:unknown) {return new Request('http://localhost/api/decision-sleeve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});}

test('actual schema 1.4 API subprocess result equals adapter',async()=>{const response=await POST(request({decision_amount_0g:1000,evidence_mode:'SYNTHETIC_EVALUATION_ONLY'}));assert.equal(response.status,200);assert.deepEqual(await response.json(),synthetic);});
test('default API is fail-closed production, not synthetic',async()=>{const response=await POST(request({decision_amount_0g:1000}));assert.equal(response.status,200);assert.deepEqual(await response.json(),prod);assert.equal(prod.recommendation.idle_weight,'1');});
test('API preserves horizon and optional deadline independently',async()=>{const response=await POST(request({decision_amount_0g:1000,holding_horizon_days:30,cash_deadline_days:1,evidence_mode:'SYNTHETIC_EVALUATION_ONLY'}));const q=parseFinalResponse(await response.text());assert.equal(q.input.holding_horizon_days,'30');assert.equal(q.input.cash_deadline_days,'1');});
for(const body of [{decision_amount_0g:0},{decision_amount_0g:'1000'},{decision_amount_0g:1000,holding_horizon_days:0},{decision_amount_0g:1000,cash_deadline_days:-1},{decision_amount_0g:1000,evidence_mode:'LIVE'},{decision_amount_0g:1000,profile:['Balanced']},{decision_amount_0g:1000,existing_holdings:100},null,[]]) test(`invalid request rejected: ${JSON.stringify(body)}`,async()=>assert.equal((await POST(request(body))).status,400));
test('contract rejects unsupported version',()=>assert.throws(()=>parseFinalResponse(JSON.stringify({...prod,schema_version:'1.2'}))));
test('contract rejects unavailable numerical zero',()=>{const q=structuredClone(prod);q.recommendation.economics.expected_net_profit_usd={state:'NOT_ASSESSED',value:null,unit:'USD',basis:'MISSING'};const value:unknown=JSON.parse(JSON.stringify(q));const obj=value as {recommendation:{economics:{expected_net_profit_usd:{value:unknown}}}};obj.recommendation.economics.expected_net_profit_usd.value='0';assert.throws(()=>parseFinalResponse(JSON.stringify(value)));});
test('contract rejects positive Ascend',()=>{const q=structuredClone(prod);q.recommendation.allocation_weights.ASCEND_STAKE_A0G='0.1';q.recommendation.idle_weight='0.9';assert.throws(()=>parseFinalResponse(JSON.stringify(q)));});
test('contract rejects duplicate or absent strategies',()=>{const q=structuredClone(prod);q.strategies[1]=q.strategies[0];assert.throws(()=>parseFinalResponse(JSON.stringify(q)));});
test('contract rejects promoted readiness',()=>{const q:unknown=JSON.parse(JSON.stringify(prod));const x=q as {readiness:{execution_readiness:string}};x.readiness.execution_readiness='EXECUTION_READY';assert.throws(()=>parseFinalResponse(JSON.stringify(q)));});
test('contract rejects production allocation',()=>{const q=structuredClone(synthetic);q.input.evidence_mode='PRODUCTION';q.evidence.mode='PRODUCTION';assert.throws(()=>parseFinalResponse(JSON.stringify(q)));});
test('decision amount replaces portfolio value label',()=>{assert.match(page,/Decision Amount \(0G\)/);assert.doesNotMatch(page,/Portfolio Value|Portfolio value/);});
test('scope banner and exogenous holdings qualification',()=>{assert.match(page,/Scope: Decision Sleeve/);assert.match(page,/Existing positions are not rebalanced/);assert.equal(prod.run_scope.whole_portfolio_compliance,'NOT_ASSESSED');});
test('synthetic evidence banner is prominent',()=>{assert.match(html,/Synthetic Evaluation Only/);assert.match(html,/Not live market evidence or execution readiness/);});
test('idle is a valid recommendation',()=>{assert.match(idleHtml,/Keep 100% Idle/);assert.doesNotMatch(idleHtml,/Optimization Failed/);});
test('all five strategies plus idle remain visible',()=>{for(const s of synthetic.strategies)assert.ok(html.includes(s.display_name));assert.match(html,/>Idle</);assert.deepEqual(synthetic.strategies.map(s=>s.strategy_id),[...STRATEGY_IDS]);});
test('Ascend is visibly CLOSED',()=>assert.match(html,/Ascend Staking[\s\S]*CLOSED/));
test('missing economics renders not assessed, not zero dollars',()=>{assert.match(idleHtml,/Expected Net Profit<\/dt><dd>Not assessed/);assert.equal(displayMeasurement(prod.recommendation.economics.expected_net_profit_usd),'Not assessed');});
test('final LP absolute stress namespace only',()=>{assert.match(html,/LP Absolute Stress/);assert.doesNotMatch(readFileSync('src/app/decision-view.tsx','utf8'),/lp_stress_loss_20pct|max_portfolio_lp_il_stress|LP ±20/);});
test('deadline input describes exit delay, not holding horizon',()=>{assert.match(page,/Optional Cash Deadline/);assert.match(page,/from exit decision until native 0G/);});
for(const [state,label] of [['NOT_REQUESTED','Not requested'],['COMPATIBLE_MODELLED','Compatible (modelled)'],['INCOMPATIBLE_MODELLED','Incompatible (modelled)'],['UNRESOLVED','Unresolved']] as const) test(`typed deadline ${state}`,()=>assert.equal(deadlineLabel(state),label));
test('modelled time-to-cash and horizon rendered distinctly',()=>{assert.match(html,/Holding horizon: 90 days/);assert.match(html,/modelled time-to-cash/);assert.match(html,/not a withdrawal guarantee/);});
test('tight deadline removes async allocations',()=>{assert.equal(tight.recommendation.allocation_weights.NATIVE_STAKE_0G,'0');assert.equal(tight.recommendation.allocation_weights.GIMO_STAKE_0G,'0');assert.equal(tight.strategies[0].liquidity.deadline_state,'INCOMPATIBLE_MODELLED');});
test('binding constraints rendered',()=>assert.match(html,/Binding Constraints/));
test('readiness proof and whole-portfolio separation',()=>{assert.match(html,/Execution readiness/);assert.match(html,/Public\/live proof/);assert.match(html,/Whole-portfolio compliance/);assert.match(html,/NOT_ASSESSED/);assert.match(html,/NOT_ESTABLISHED/);});
test('current-input comparison warns capability limitations',()=>{assert.match(html,/Current-input Legacy Comparison/);assert.match(html,/not always directly equivalent/);assert.match(html,/Comparability: LIMITED/);assert.equal(synthetic.comparison.legacy_linear.state==='ASSESSED'?synthetic.comparison.legacy_linear.cash_deadline:null,'NOT_SUPPORTED');});
test('long diagnostics wrap and expand',()=>{assert.match(html,/<details/);assert.match(css,/overflow-wrap:anywhere/);assert.match(css,/@media\(max-width:760px\)/);assert.match(css,/minmax\(0,1fr\)/);});
test('no report artifacts or benchmark statistics in frontend',()=>{function all(dir:string):string[]{return readdirSync(dir,{withFileTypes:true}).flatMap(v=>v.isDirectory()?all(path.join(dir,v.name)):[path.join(dir,v.name)]);}const source=all('src').map(f=>readFileSync(f,'utf8')).join('\n');assert.doesNotMatch(source,/final_figures|final_tables|final_evaluation_findings_iteration24|final_evaluation_findings\.json|27\/49|\$43\.40/);assert.doesNotMatch(page,/45|49|196|benchmark/i);});
test('no wallet or public execution milestone UI',()=>assert.doesNotMatch(page,/Connect Wallet|Approve|Execute|live allocation|Live routes/i));
test('malformed JSON is a technical request error',async()=>{const res=await POST(new Request('http://localhost/api/decision-sleeve',{method:'POST',body:'{'}));assert.equal(res.status,400);});
test('API subprocess failure stays separate from valid idle',async()=>{const prior=process.env.PYTHON_BIN;process.env.PYTHON_BIN='/nonexistent-iteration25-python';try{const res=await POST(request({decision_amount_0g:1000}));assert.equal(res.status,500);assert.equal((await res.json() as {error:string}).error,'Optimizer API error');}finally {if(prior===undefined)delete process.env.PYTHON_BIN;else process.env.PYTHON_BIN=prior;}});

test('malformed comparison does not default missing allocations to zero',()=>{const q:unknown=JSON.parse(JSON.stringify(synthetic));const legacy=(q as {comparison:{legacy_linear:Record<string,unknown>}}).comparison.legacy_linear;delete legacy.allocation_weights;assert.throws(()=>parseFinalResponse(JSON.stringify(q)));});

for(const sid of STRATEGY_IDS) test(`canonical metadata accepted independently of gate: ${sid}`,()=>{const row=synthetic.strategies.find(s=>s.strategy_id===sid);assert.ok(row);assert.equal(row.canonical_state,sid==='ASCEND_STAKE_A0G'?'INTEGRATED_GATED':'INTEGRATED_ALLOCATABLE');assert.equal(row.allocation_gate,sid==='ASCEND_STAKE_A0G'?'CLOSED':'CONDITIONAL');assert.equal(row.structural_candidate,true);assert.equal(row.integration_state,'IMPLEMENTED');assert.equal(row.protocol_availability,'LIVE');assert.deepEqual(parseFinalResponse(JSON.stringify(synthetic)),synthetic);});
test('parser rejects invented canonical category',()=>{const q=JSON.parse(JSON.stringify(synthetic)) as {strategies:Record<string,unknown>[]};q.strategies[0].canonical_state='INTEGRATED_CONDITIONAL';assert.throws(()=>parseFinalResponse(JSON.stringify(q)));});
test('parser rejects lost integration or structural dimension',()=>{for(const [key,value] of [['integration_state','NOT_INTEGRATED'],['structural_candidate',false]]) {const q=JSON.parse(JSON.stringify(synthetic)) as {strategies:Record<string,unknown>[]};q.strategies[0][String(key)]=value;assert.throws(()=>parseFinalResponse(JSON.stringify(q)));}});
test('parser still rejects an open Ascend gate',()=>{const q=JSON.parse(JSON.stringify(synthetic)) as {strategies:Record<string,unknown>[]};q.strategies[4].allocation_gate='CONDITIONAL';assert.throws(()=>parseFinalResponse(JSON.stringify(q)));});
test('rendered canonical category and gate remain separate',()=>{assert.match(html,/Canonical state: Integrated allocatable · Allocation gate: CONDITIONAL/);assert.match(html,/Canonical state: Integrated gated · Allocation gate: CLOSED/);assert.match(html,/external protocol only, not capstone execution proof/);});
