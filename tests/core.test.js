import test from 'node:test';
import assert from 'node:assert/strict';
import {validate,generatePlan,SAMPLE} from '../dist/core.js';
const plan=actions=>({message:'',actions});
const a=(command,args={})=>({command,args});
const ok=()=>new Response(JSON.stringify({candidates:[{finishReason:'STOP',content:{parts:[{text:JSON.stringify(SAMPLE)}]}}]}));
test('accepts sample with two action domains',()=>assert.equal(validate(SAMPLE).actions.length,2));
test('rejects unexpected commands, keys, primitive values and inherited names',()=>{
  for(const value of [null,[],{},plan([a('shell')]),plan([a('constructor')]),plan([a('list_tasks',{extra:1})]),plan([a('add_task',{title:1})]),plan([a('delete_task',{id:true})]),plan([a('delete_task',{id:-1})]),{message:'',actions:[],extra:1}]) assert.throws(()=>validate(value));
});
test('rejects path traversal, absolute paths, and executable file extensions',()=>{
 for(const path of ['../secret.txt','/tmp/x.txt','a/b.txt','file.js','a\\b.txt','<script>.txt']) assert.throws(()=>validate(plan([a('write_file',{path,content:'x'})])));
});
test('rejects excessive action and content counts',()=>{assert.throws(()=>validate(plan(Array(11).fill(a('list_tasks')))));assert.throws(()=>validate(plan([a('write_file',{path:'a.txt',content:'x'.repeat(20001)})])));});
test('returns valid live plan and authenticates request',async()=>{let call;const result=await generatePlan('make a note','test-key','test-model',{},()=>{},async(...args)=>{call=args;return ok();});assert.deepEqual(result,SAMPLE);assert.equal(call[1].headers['x-goog-api-key'],'test-key');});
test('retries 503 then succeeds',async()=>{let calls=0;await generatePlan('request','key','model',{},()=>{},async()=>++calls<3?new Response('',{status:503}):ok(),async()=>{});assert.equal(calls,3);});
test('does not retry auth failures',async()=>{let calls=0;await assert.rejects(()=>generatePlan('request','key','model',{},()=>{},async()=>{calls++;return new Response('',{status:403});},async()=>{}),/403/);assert.equal(calls,1);});
test('bounded 503 retries and actionable error',async()=>{let calls=0;await assert.rejects(()=>generatePlan('request','key','model',{},()=>{},async()=>{calls++;return new Response('',{status:503});},async()=>{}),/temporarily unavailable/);assert.equal(calls,4);});
test('honors numeric Retry-After',async()=>{let calls=0,delay;await generatePlan('request','key','model',{},()=>{},async()=>++calls===1?new Response('',{status:429,headers:{'Retry-After':'5'}}):ok(),async ms=>{delay=ms;});assert.equal(delay,5000);});
test('stops on long Retry-After',async()=>{await assert.rejects(()=>generatePlan('request','key','model',{},()=>{},async()=>new Response('',{status:429,headers:{'Retry-After':'120'}}),async()=>{}),/120 seconds/);});
test('rejects malformed model output',async()=>{await assert.rejects(()=>generatePlan('request','key','model',{},()=>{},async()=>new Response('{bad')),/non-JSON/);});
test('fails network requests after bounded retries',async()=>{let calls=0;await assert.rejects(()=>generatePlan('request','key','model',{},()=>{},async()=>{calls++;throw Error('offline');},async()=>{}),/Cannot reach/);assert.equal(calls,4);});
