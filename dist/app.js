import {validate, generatePlan, SAMPLE} from './core.js';
const $=id=>document.getElementById(id);
let db, pending=null, busy=false, mode='live';
const emptyState=()=>({notes:[],tasks:[],audit:[],nextId:1});
const entry=(event,details={})=>({time:new Date().toISOString(),event,...details});
function openDB(){return new Promise((resolve,reject)=>{const r=indexedDB.open('study-action-agent',1);r.onupgradeneeded=()=>r.result.createObjectStore('state');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
function transact(change){return new Promise((resolve,reject)=>{
  const tx=db.transaction('state',change?'readwrite':'readonly'), store=tx.objectStore('state');let result;
  const req=store.get('workspace');
  req.onsuccess=()=>{try{const state=req.result||emptyState();result=change?change(state):state;if(change)store.put(state,'workspace');}catch(e){reject(e);tx.abort();}};
  tx.oncomplete=()=>resolve(result);tx.onerror=()=>reject(tx.error||Error('Unable to save browser data.'));tx.onabort=()=>reject(tx.error||Error('Workspace update was cancelled.'));
});}
const audit=(event,details={})=>transact(s=>{s.audit.push(entry(event,details));});
function status(text,error=false){$('status').textContent=text;$('status').className=error?'error':'success';}
function lock(value){busy=value;for(const id of ['planButton','sampleButton','approveButton','cancelButton','request','settingsButton'])$(id).disabled=value;}
function download(name,text,type='text/plain') {const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function el(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;}
function clearPlan(){pending=null;$('planPanel').hidden=true;$('emptyPlan').hidden=false;$('planOrigin').textContent='Waiting for a request';}
function setPlan(plan,origin){validate(plan);pending=plan;mode=origin;$('emptyPlan').hidden=true;$('planPanel').hidden=false;$('planOrigin').textContent=origin==='live'?'Gemini · live':'Fixed sample · no LLM';$('planMessage').textContent=plan.message;$('planJson').textContent=JSON.stringify(plan,null,2);$('actions').replaceChildren();for(const a of plan.actions){const li=el('li');li.append(el('strong',a.command.replaceAll('_',' ')),el('pre',JSON.stringify(a.args,null,2)));$('actions').append(li);}$('approveButton').hidden=!plan.actions.length;}
async function render(){const state=await transact();$('noteCount').textContent=state.notes.length;$('taskCount').textContent=state.tasks.length;
  $('notes').replaceChildren();if(!state.notes.length)$('notes').append(el('p','Your created notes will appear here.','placeholder'));
  for(const note of state.notes){const box=el('div',undefined,'item'),head=el('div',undefined,'item-head');head.append(el('strong',note.path));const button=el('button','Download','text-button');button.onclick=async()=>{try{await audit('download_requested',{path:note.path});download(note.path,note.content);await render();}catch(e){status(e.message,true);}};head.append(button);const details=el('details');details.append(el('summary','Read note'),el('pre',note.content));box.append(head,details);$('notes').append(box);}
  $('tasks').replaceChildren();if(!state.tasks.length)$('tasks').append(el('p','Tasks stay here after you refresh.','placeholder'));
  for(const task of state.tasks){const item=el('div',undefined,'item');item.append(el('span',`#${task.id}`,'task-id'),el('span',task.title,task.done?'done':''),el('div',task.done?'✓ Complete':'○ To do','helper'));$('tasks').append(item);}
  $('audit').replaceChildren();if(!state.audit.length)$('audit').append(el('p','Actions and outcomes appear here.','placeholder'));
  for(const log of state.audit.slice(-30).reverse()){const row=el('div',undefined,'audit-item');row.append(el('strong',log.event.replaceAll('_',' ')+(log.command?' · '+log.command:'')),el('br'),el('small',new Date(log.time).toLocaleTimeString()+(log.path?' · '+log.path:'')+(log.id?' · #'+log.id:'')));$('audit').append(row);}
}
function confirmChange(text){return new Promise(resolve=>{const dialog=$('destructive');$('destructiveText').textContent=text;dialog.returnValue='cancel';dialog.addEventListener('close',()=>resolve(dialog.returnValue==='confirm'),{once:true});dialog.showModal();});}
async function execute(action){validate({message:'',actions:[action]});const {command,args}=action;const identity={};if(args.path)identity.path=args.path;if(args.id)identity.id=args.id;
  await audit('attempt',{command,...identity,mode});
  try{
    const snapshot=await transact();const old=snapshot.notes.find(n=>n.path===args.path);
    const destructive=command.startsWith('delete_')||(command==='write_file'&&old);
    if(destructive&&!await confirmChange(`${command.replaceAll('_',' ')}: ${args.path||'task #'+args.id}`)){await audit('cancelled',{command,...identity,mode});return {cancelled:true,result:'Cancelled. Remaining actions stopped.'};}
    const result=await transact(s=>{
      let result;const index=s.notes.findIndex(n=>n.path===args.path),task=s.tasks.find(t=>t.id===args.id);
      // If another tab changed the target after preview/confirmation, stop rather than overwrite newer work.
      if(['write_file','delete_file'].includes(command)&&JSON.stringify(s.notes[index])!==JSON.stringify(old))throw Error('This note changed in another tab. Generate a new plan.');
      switch(command){
        case 'write_file':
          if(index<0&&s.notes.length>=200)throw Error('Workspace limit: 200 notes. Delete unused notes first.');
          if(index<0)s.notes.push({path:args.path,content:args.content});else s.notes[index]={path:args.path,content:args.content};result=`Saved ${args.path}. Use Download to save a .txt file to your computer.`;break;
        case 'read_file':if(index<0)throw Error('Note not found.');result=s.notes[index].content;break;
        case 'list_files':result=s.notes.map(n=>n.path);break;
        case 'delete_file':if(index<0)throw Error('Note not found.');s.notes.splice(index,1);result=`Deleted ${args.path}.`;break;
        case 'add_task':if(s.tasks.length>=200)throw Error('Workspace limit: 200 tasks.');const id=s.nextId++;s.tasks.push({id,title:args.title,done:false});result=`Added task #${id}: ${args.title}`;break;
        case 'list_tasks':result=s.tasks;break;
        case 'complete_task':if(!task)throw Error('Task ID does not exist.');task.done=true;result=`Completed task #${task.id}.`;break;
        case 'delete_task':if(!task)throw Error('Task ID does not exist.');s.tasks=s.tasks.filter(t=>t.id!==args.id);result=`Deleted task #${args.id}.`;break;
      }
      s.audit.push(entry('success',{command,...identity,mode}));return structuredClone(result);
    });return {result};
  }catch(e){await audit('failed',{command,...identity,mode,error:e.message});throw e;}
}
$('settingsButton').onclick=()=>$('settings').showModal();
$('saveSettings').onclick=()=>{const ready=!!$('key').value.trim();$('connection').textContent=ready?'Key set · live mode':'Key needed';$('connection').className='pill'+(ready?' live':'');};
$('clearKey').onclick=()=>{$('key').value='';$('connection').textContent='Key needed';$('connection').className='pill';};
for(const button of document.querySelectorAll('[data-example]'))button.onclick=()=>{if(!busy){$('request').value=button.dataset.example;$('request').focus();}};
$('planButton').onclick=async()=>{
  if(!$('key').value.trim()){$('settings').showModal();return;}
  lock(true);clearPlan();$('results').replaceChildren();status('Asking Gemini for a plan…');
  try{await audit('request_received',{mode:'live'});const s=await transact();const plan=await generatePlan($('request').value,$('key').value.trim(),$('model').value.trim(),{note_names:s.notes.map(n=>n.path),tasks:s.tasks},status);await audit('plan_validated',{mode:'live',count:plan.actions.length});setPlan(plan,'live');status(plan.actions.length?'Review the actions below before approving.':'No actions proposed. Check the explanation.');}
  catch(e){await audit('planning_failed',{error:e.message});status(e.message,true);}
  finally{lock(false);await render();}
};
$('sampleButton').onclick=async()=>{try{clearPlan();$('results').replaceChildren();const plan=structuredClone(SAMPLE);await audit('plan_validated',{mode:'sample',count:plan.actions.length});setPlan(plan,'sample');status('Fixed sample loaded. Approval will create real notes and tasks.');await render();}catch(e){status(e.message,true);}};
$('cancelButton').onclick=async()=>{try{await audit('plan_cancelled',{mode});clearPlan();status('Plan cancelled. No actions executed.');await render();}catch(e){status(e.message,true);}};
$('approveButton').onclick=async()=>{if(!pending||busy)return;lock(true);const plan=pending;pending=null;
  try{validate(plan);await audit('plan_approved',{mode});let stopped=false;for(let i=0;i<plan.actions.length;i++){status(`Executing ${i+1}/${plan.actions.length}: ${plan.actions[i].command}…`);const {result,cancelled}=await execute(plan.actions[i]);const row=el('div',undefined,'result');row.append(el('strong',plan.actions[i].command.replaceAll('_',' ')),el('pre',typeof result==='string'?result:JSON.stringify(result,null,2)));$('results').append(row);await render();if(cancelled){stopped=true;break;}}clearPlan();status(stopped?'Cancelled. Earlier successful actions remain.':'Done. Results are saved in your browser workspace.');}
  catch(e){clearPlan();status(`${e.message} Remaining actions stopped; earlier successful actions remain.`,true);}
  finally{lock(false);await render();}
};
$('exportAudit').onclick=async()=>{try{await audit('audit_export_requested');const state=await transact();download('agent-audit.json',JSON.stringify(state.audit,null,2),'application/json');await render();}catch(e){status(e.message,true);}};
try{db=await openDB();await render();}catch{status('Browser storage is unavailable. Enable site storage to use this app.',true);lock(true);}
