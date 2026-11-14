/* POLARIS Administration — reviewed requests & authoritative Supabase sessions. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
let cfg=null,session=null,operator=null,factorId=null,challengeId=null,refreshTimer=null,queue=[],sessions=[],busy=false;
const notify=(msg,type='')=>{const box=$('status');box.className='notice'+(type?' '+type:'');box.textContent=msg};
const show=(id)=>['loginPanel','mfaPanel','dashboard'].forEach(view=>$(view).classList.toggle('hidden',view!==id));
const headers=token=>({'apikey':cfg.publishable_key,'Authorization':'Bearer '+(token||cfg.publishable_key),'Content-Type':'application/json'});
async function auth(route,method='GET',body){const r=await fetch(cfg.supabase_url+'/auth/v1'+route,{method,headers:headers(session?.access_token),cache:'no-store',body:body?JSON.stringify(body):undefined});
 const data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.msg||data.error_description||data.message||'Authentication failed');return data}
async function endpoint(path,opts={}){if(!session?.access_token)throw Error('Session expired');const r=await fetch('/api/'+path,{method:opts.method||'GET',cache:'no-store',
 headers:{'Authorization':'Bearer '+session.access_token,'Content-Type':'application/json'},body:opts.body?JSON.stringify(opts.body):undefined});
 const data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.detail||'Secure request denied');return data}
function uiState(state){$('authState').textContent=state}
async function init(){try{const r=await fetch('/api/workspace-config',{cache:'no-store'});cfg=await r.json();if(!cfg.available)throw Error('Identity service unavailable');show('loginPanel');notify('Administration is restricted to verified POLARIS administrators with MFA.')}catch(e){notify(e.message,'error')}}
async function login(e){e.preventDefault();$('loginButton').disabled=true;notify('Validating administrator account…');try{session=await auth('/token?grant_type=password','POST',{email:$('email').value.trim(),password:$('password').value});$('password').value='';
 const factors=await auth('/factors');const verified=(factors.totp||[]).filter(f=>f.status==='verified');
 if(verified.length){factorId=verified[0].id;}else{const enrol=await auth('/factors','POST',{factor_type:'totp',friendly_name:'POLARIS Admin TOTP'});
 factorId=enrol.id;const qr=enrol.totp?.qr_code||'';if(!qr.startsWith('data:image/'))throw Error('Authenticator QR code unavailable');$('mfaQr').src=qr;$('enrollment').classList.remove('hidden');}
 const challenge=await auth('/factors/'+encodeURIComponent(factorId)+'/challenge','POST',{});challengeId=challenge.id;show('mfaPanel');notify('Complete the administrator TOTP challenge.');
 }catch(e){session=null;notify('Access denied: '+e.message,'error')}finally{$('loginButton').disabled=false}}
async function verify(e){e.preventDefault();try{const code=$('totp').value.trim();if(!/^\d{6}$/.test(code))throw Error('Six digits required');
 const result=await auth('/factors/'+encodeURIComponent(factorId)+'/verify','POST',{challenge_id:challengeId,code});
 if(!result.access_token)throw Error('Multi-factor verification unsuccessful');session={...session,...result};$('totp').value='';$('mfaQr').removeAttribute('src');
 const person=await endpoint('private/whoami');if(person.role!=='administrator')throw Error('This account is not authorized as a POLARIS administrator');operator=person;
 $('adminName').textContent=person.name+' · authenticated administrator';$('signOut').classList.remove('hidden');uiState('ADMIN · MFA');show('dashboard');await loadAll();
 refreshTimer=setInterval(()=>{if(session&&!busy)loadAll()},30000);
 }catch(e){notify('MFA or administrator verification failed: '+e.message,'error');if(session?.access_token){await signOut()}}}
async function signOut(){if(refreshTimer)clearInterval(refreshTimer);refreshTimer=null;try{if(session?.access_token)await auth('/logout','POST',{});}catch(_){ }session=null;operator=null;factorId=null;challengeId=null;queue=[];sessions=[];uiState('RESTRICTED');$('signOut').classList.add('hidden');show('loginPanel');notify('Signed out. Account credentials are not retained by this page.');}
const time=v=>v?new Date(v).toLocaleString('en-GB',{timeZone:'UTC',year:'numeric',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false})+' UTC':'—';
function element(tag,text,cls){const e=document.createElement(tag);e.textContent=String(text??'—');if(cls)e.className=cls;return e}
function stateBadge(value){return element('span',value,'status-badge '+value)}
function emptyRow(tbody,text,colspan){const tr=document.createElement('tr'),td=element('td',text,'empty');td.colSpan=colspan;tr.append(td);tbody.append(tr)}
function renderRequests(){const data=$('requestFilter').value==='all'?queue:queue.filter(r=>r.status===$('requestFilter').value),body=$('requestRows');body.replaceChildren();
 if(!data.length)return emptyRow(body,'No requests for this filter',5);
 for(const row of data){const tr=document.createElement('tr');tr.append(element('td',row.first_name+' '+row.last_name),element('td',row.staff_id),element('td',time(row.created_at)));
 const status=document.createElement('td');status.append(stateBadge(row.status));tr.append(status);
 const action=document.createElement('td');if(row.status==='pending'){const group=document.createElement('div');group.className='table-actions';
 for(const [value,label,cls] of [['approved','Approve','approve'],['rejected','Reject','reject']]){const b=element('button',label,cls);b.type='button';b.addEventListener('click',()=>decide(row,value));group.append(b)}action.append(group)}else action.append(element('span',time(row.reviewed_at),'muted'));tr.append(action);body.append(tr)}}
function renderDirectory(){const target=$('directoryRows');target.replaceChildren();const q=$('userSearch').value.trim().toLowerCase();const filtered=queue.filter(x=>!q||[x.first_name,x.last_name,x.staff_id].join(' ').toLowerCase().includes(q));
 if(!filtered.length)return emptyRow(target,'No matching engineers',6);
 for(const row of filtered){const tr=document.createElement('tr');tr.append(element('td',row.first_name),element('td',row.last_name),element('td',row.staff_id));const st=document.createElement('td');st.append(stateBadge(row.status));tr.append(st,element('td',time(row.created_at)),element('td',time(row.reviewed_at)));target.append(tr)}}
function renderSessions(){const target=$('sessionRows');target.replaceChildren();$('sessionCount').textContent=sessions.length+' recent authentication sessions';
 if(!sessions.length)return emptyRow(target,'No authentication sessions recorded',5);
 for(const row of sessions){const tr=document.createElement('tr');tr.append(element('td',row.first_name),element('td',row.last_name),element('td',row.staff_id));const st=document.createElement('td');st.append(stateBadge(row.account_status||'unregistered'));tr.append(st,element('td',time(row.session_created_at)));target.append(tr)}}
async function loadAll(){if(busy)return;busy=true;try{const [a,b]=await Promise.all([endpoint('admin/requests'),endpoint('admin/sessions')]);queue=a.requests||[];sessions=b.sessions||[];
 $('pendingMetric').textContent=queue.filter(r=>r.status==='pending').length;
 $('approvedMetric').textContent=queue.filter(r=>r.status==='approved').length;
 $('rejectedMetric').textContent=queue.filter(r=>r.status==='rejected').length;
 $('sessionsMetric').textContent=sessions.filter(r=>Date.now()-Date.parse(r.session_created_at)<86400000).length;
 $('refreshedAt').textContent='UPDATED '+new Date().toLocaleTimeString('en-GB',{hour12:false});renderRequests();renderDirectory();renderSessions();
 notify('Access directory and authenticated session history synchronized.','success');}catch(e){notify('Administration data unavailable: '+e.message,'error')}finally{busy=false}}
async function decide(row,status){if(busy)return;const verb=status==='approved'?'Approve':'Reject';if(!confirm(verb+' '+row.first_name+' '+row.last_name+' ('+row.staff_id+')?'))return;
 busy=true;notify('Recording '+status+' accreditation decision…');try{await endpoint('admin/requests/'+encodeURIComponent(row.user_id)+'/decision',{method:'POST',body:{status}});busy=false;await loadAll();
 }catch(e){notify('Decision not saved: '+e.message,'error');busy=false}}
function tab(name){const tabs={requests:['tabRequests','requestsView'],directory:['tabDirectory','directoryView'],sessions:['tabSessions','sessionsView']};
 for(const [key,[button,view]]of Object.entries(tabs)){$(view).classList.toggle('hidden',name!==key);$(button).classList.toggle('active',name===key);$(button).setAttribute('aria-pressed',String(name===key))}}
$('loginForm').addEventListener('submit',login);$('mfaForm').addEventListener('submit',verify);$('signOut').addEventListener('click',signOut);
$('refreshAll').addEventListener('click',loadAll);$('requestFilter').addEventListener('change',renderRequests);$('userSearch').addEventListener('input',renderDirectory);
$('tabRequests').addEventListener('click',()=>tab('requests'));$('tabDirectory').addEventListener('click',()=>tab('directory'));$('tabSessions').addEventListener('click',()=>tab('sessions'));
init();
})();
