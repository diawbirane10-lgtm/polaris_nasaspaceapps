/* POLARIS — Authenticated mission workspace. No credentials in localStorage. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
let config=null, session=null, identity=null, pendingFactor=null, challengeId=null,
    activeId=null,liveSocket=null, heartbeat=null, latestReview=null, reconnectAttempt=0,signingOut=false,
    approvalTimer=null, approvalState=null;
const urls={auth:'/auth/v1',realtime:'/realtime/v1/websocket'};
const safeMessage=(message,error=false)=>{$('message').textContent=message;$('message').className='status'+(error?' error':'')};
function view(name){['loginSection','pendingSection','mfaSection','workspaceSection'].forEach(x=>$(x).classList.toggle('hidden',x!==name));$('intro').classList.toggle('hidden',name==='workspaceSection')}
function busy(id,val){$(id).disabled=val}
function accessTab(name){const signup=name==='signup';$('loginForm').classList.toggle('hidden',signup);$('signupForm').classList.toggle('hidden',!signup);
 $('showSignin').classList.toggle('active',!signup);$('showSignin').setAttribute('aria-pressed',String(!signup));
 $('showSignup').classList.toggle('active',signup);$('showSignup').setAttribute('aria-pressed',String(signup));
 $('accessInstructions').textContent=signup?'Submit your details for accreditation. Email verification and administrator approval are required.':'Sign in to your approved account, or create a new registration request.'}
function approvalLabel(state){const badge=$('approvalBadge');badge.className='approval-state '+(state==='approved'?'approved':state==='rejected'?'rejected':'pending');badge.textContent=state.toUpperCase();}
function stopApprovalPolling(){if(approvalTimer){clearInterval(approvalTimer);approvalTimer=null}}
async function accessStatus(){if(!session?.access_token)throw Error('Sign in first');const r=await fetch('/api/access/status',{headers:{Authorization:'Bearer '+session.access_token},cache:'no-store'});
 const j=await r.json().catch(()=>({}));if(!r.ok)throw Error(j.detail||'Unable to retrieve account status');return j;}
async function refreshApproval(){if(!session?.access_token)return;try{const response=await accessStatus();approvalState=response.status;
 approvalLabel(response.status);$('approvalDetails').textContent=(response.first_name?response.first_name+' '+response.last_name+' · '+response.staff_id+'. ':'')+
 (response.status==='pending'?'Waiting for administrator review.':response.status==='rejected'?'Request rejected. Contact the workspace administrator.':response.status==='approved'?'Approved. Complete MFA verification to access your missions.':'No registration request found. Contact the administrator.');
 if(response.status==='approved'){stopApprovalPolling();$('proceedMfa').classList.remove('hidden');safeMessage('Access approved. Continue with multi-factor authentication to open the workspace.');}
 else if(response.status==='rejected'){stopApprovalPolling();$('proceedMfa').classList.add('hidden');safeMessage('Your request was rejected. Access is not granted.',true)}
 else{$('proceedMfa').classList.add('hidden');safeMessage('Signed in. Workspace access is '+response.status+'.')}
 }catch(e){safeMessage('Status unavailable: '+e.message,true)}}
async function beginMfa(){const factorState=await authCall('/factors');const candidates=(factorState?.totp||[]).filter(x=>x.status==='verified');
 if(candidates.length){pendingFactor=candidates[0].id;await startChallenge();}
 else{const enrol=await authCall('/factors',{method:'POST',body:{factor_type:'totp',friendly_name:'POLARIS Mission Workspace'}});
  pendingFactor=enrol.id;$('enrolPane').classList.remove('hidden');const qr=enrol.totp?.qr_code||'';
  if(!qr.startsWith('data:image/svg+xml')&&!qr.startsWith('data:image/png'))throw Error('TOTP setup image missing');
  $('mfaQr').src=qr;$('mfaSecretHint').textContent='Keep the authenticator secret private. Enter a six-digit code to continue.';
  await startChallenge();}}
async function register(e){e.preventDefault();busy('signupBtn',true);safeMessage('Submitting a secure access request…');try{
 const first=$('firstName').value.trim(),last=$('lastName').value.trim(),staff=$('staffId').value.trim();
 if(!/^[a-zA-Z0-9][a-zA-Z0-9._-]{2,31}$/.test(staff))throw Error('Employee ID must be 3–32 letters, digits, dots, dashes or underscores');
 if(!$('acceptTerms').checked)throw Error('You must accept the terms.');
 await authCall('/signup',{method:'POST',token:config.publishable_key,body:{email:$('signupEmail').value.trim(),password:$('signupPassword').value,
 data:{polaris_signup:'true',first_name:first,last_name:last,staff_id:staff,accepted_terms:'true',terms_version:'polaris-2026-11-14'}}});
 $('signupPassword').value='';accessTab('signin');$('email').value=$('signupEmail').value.trim();
 safeMessage('If this account is newly created, verify your email if prompted, then sign in to check its accreditation status. Existing accounts can sign in directly; no mission access is granted without approval.');
 }catch(e){safeMessage('Registration not completed: '+e.message,true)}finally{busy('signupBtn',false)}}

function authHeaders(token){return {'apikey':config.publishable_key,'Authorization':'Bearer '+token,'Content-Type':'application/json'}}
async function authCall(route,{method='GET',body,token=session?.access_token}={}){
  const r=await fetch(config.supabase_url+urls.auth+route,{method,headers:authHeaders(token||config.publishable_key),
    body:body?JSON.stringify(body):undefined,cache:'no-store'});
  const j=await r.json().catch(()=>({}));if(!r.ok)throw Error(j.msg||j.error_description||j.message||'Identity provider rejected request');return j;
}
async function api(route,{method='GET',body,blob=false}={}){
 if(!session?.access_token)throw Error('Session expired. Please sign in again.');
 const r=await fetch('/api/private/'+route,{method,headers:{Authorization:'Bearer '+session.access_token,'Content-Type':'application/json'},
  cache:'no-store',body:body?JSON.stringify(body):undefined});
 if(!r.ok){const d=await r.json().catch(()=>({}));throw Error(d.detail||'Workspace request unsuccessful')}
 return blob?r.blob():r.json();
}
async function init(){try{
 const r=await fetch('/api/workspace-config',{cache:'no-store'});config=await r.json();
 if(!config.available)throw Error('The workspace requires a POLARIS Supabase connection. The public demonstration remains available.');
 view('loginSection');safeMessage('Workspace online · Authenticated access required.');
 }catch(e){safeMessage(e.message,true)}}
async function login(e){e.preventDefault();busy('loginBtn',true);safeMessage('Verifying credentials…');try{
 const result=await authCall('/token?grant_type=password',{method:'POST',body:{email:$('email').value.trim(),password:$('password').value}});
 session=result;$('password').value='';$('sessionState').textContent='ACCOUNT AUTHENTICATED';$('logout').classList.remove('hidden');
 const access=await accessStatus();approvalState=access.status;
 if(access.status==='pending'||access.status==='rejected'||access.status==='approved'){
  view('pendingSection');approvalLabel(access.status);
  $('approvalDetails').textContent='Your access request: '+access.status.toUpperCase()+'.';
  if(access.status==='pending'){stopApprovalPolling();approvalTimer=setInterval(refreshApproval,15000)}
  $('proceedMfa').classList.toggle('hidden',access.status!=='approved');
  safeMessage(access.status==='pending'?'Your request is waiting for approval.':access.status==='approved'?'Account approved. Continue with MFA to access the workspace.':'Your request was rejected.',access.status==='rejected');
 }else if(access.status==='not_registered'){
  await beginMfa();
 }else{throw Error('Unrecognized account status')}
 }catch(e){session=null;stopApprovalPolling();safeMessage('Sign-in failed: '+e.message,true)}finally{busy('loginBtn',false)}}
async function startChallenge(){const q=await authCall('/factors/'+encodeURIComponent(pendingFactor)+'/challenge',{method:'POST',body:{}});
 challengeId=q.id;view('mfaSection');$('totp').value='';$('totp').focus();safeMessage('Enter the fresh six-digit code from your authenticator app.')}
async function verifyMfa(e){e.preventDefault();try{
 const code=$('totp').value.trim();if(!/^\d{6}$/.test(code))throw Error('Enter exactly six digits.');
 const out=await authCall('/factors/'+encodeURIComponent(pendingFactor)+'/verify',{method:'POST',body:{challenge_id:challengeId,code}});
 if(!out.access_token)throw Error('Authenticator did not return a verified session');
 session={...session,...out};$('totp').value='';$('mfaQr').removeAttribute('src');$('enrolPane').classList.add('hidden');
 stopApprovalPolling();const account=await api('whoami');identity=account;$('operatorLabel').textContent='Authenticated: '+account.name+'  ·  '+account.role.toUpperCase();
 $('sessionState').textContent='MFA VERIFIED';$('logout').classList.remove('hidden');view('workspaceSection');
 safeMessage('Identity verified. Your mission workspace is isolated by database access policies.');await loadMissions();startRealtime();
 }catch(e){safeMessage('MFA verification: '+e.message,true)}}
function clearState(){session=null;identity=null;activeId=null;latestReview=null;pendingFactor=null;challengeId=null;
 closeRealtime();stopApprovalPolling();$('proceedMfa').classList.add('hidden');$('sessionState').textContent='SIGN IN REQUIRED';$('logout').classList.add('hidden');view('loginSection')}
async function logout(){signingOut=true;try{if(session)await authCall('/logout',{method:'POST'})}catch(_e){}clearState();signingOut=false;safeMessage('Signed out. Session credentials cleared from this tab.')}
function fillEditor(cfg){for(const [id,value]of Object.entries(cfg||{})){const el=$(id);if(el&&value!==undefined&&value!==null)el.value=String(value)}}
function currentCfg(){return {site:$('site').value,focus:$('focus').value,start:$('start').value,delay:Number($('delay').value),
 pv:Number($('pv').value),load:Number($('load').value),battery:Number($('battery').value),minSoc:Number($('minSoc').value)}}
function selectedMission(plan){activeId=plan.id;$('activeMission').textContent='SAVED · '+plan.id.slice(0,8);
 $('missionTitle').value=plan.title;fillEditor(plan.input_configuration);latestReview=null;clearReview()}
function newMission(){activeId=null;$('activeMission').textContent='UNSAVED';$('missionTitle').value='South Pole Power & Communications Study';latestReview=null;clearReview()}
async function loadMissions(){try{const data=await api('missions');const target=$('missionList');target.replaceChildren();
 if(!data.missions.length){const p=document.createElement('p');p.textContent='No missions saved yet. Create your first plan.';p.className='muted textsmall';target.appendChild(p);return}
 for(const m of data.missions){const btn=document.createElement('button');btn.className='mission-card';btn.type='button';btn.setAttribute('aria-current',String(m.id===activeId));
 const title=document.createElement('b');title.textContent=m.title;const date=document.createElement('small');date.textContent='Updated: '+new Date(m.updated_at).toLocaleString();btn.append(title,date);btn.addEventListener('click',()=>{selectedMission(m);loadMissions()});target.appendChild(btn)}
 }catch(e){safeMessage('Unable to synchronize missions: '+e.message,true)}}
async function saveMission(e){e.preventDefault();busy('saveMission',true);try{const cfg=currentCfg(),title=$('missionTitle').value.trim();
 const resource=activeId?'missions/'+encodeURIComponent(activeId):'missions';const out=await api(resource,{method:activeId?'PATCH':'POST',body:{title,input_configuration:cfg}});
 selectedMission(out.mission);await loadMissions();safeMessage('Mission saved to your protected workspace. Revision tracked in PostgreSQL.');
 }catch(e){safeMessage('Save failed: '+e.message,true)}finally{busy('saveMission',false)}}
function reviewInput(){const v=currentCfg();return {question:'Review mission power and local visibility constraints',site:v.site,
 start:v.start,duration_hours:24,delay_hours:v.delay,pv_area_m2:v.pv,load_w:v.load,battery_kwh:v.battery,
 panel_mode:'horizontal',min_soc_pct:v.minSoc,min_local_earth_hours:6,max_local_earth_gap_hours:24,
 focus:v.focus,selected_scenarios:['original','delayed','alternative_site_after_delay'],mission_label:$('missionTitle').value.trim()}}
function clearReview(){$('resultId').textContent='NO RUN';$('results').replaceChildren();$('checksTable').classList.add('hidden');
 $('resultSummary').textContent='Recompute the mission to display current constraint results.';['briefDownload','dossierDownload'].forEach(id=>$(id).disabled=true)}
function renderReview(data){$('resultId').textContent=data.review_id||'ANALYSIS';const successes=data.scenarios.filter(s=>!s.blocking_criteria?.length).length;
 $('resultSummary').textContent=successes+' of '+data.scenarios.length+' modeled alternatives satisfy the selected numerical limits.';
 const results=$('results');results.replaceChildren();
 for(const s of data.scenarios){const card=document.createElement('div');card.className='metric';const label=document.createElement('small');label.textContent=s.label||s.key;
 const state=document.createElement('strong');state.textContent=s.blocking_criteria?.length?'REVISE':'PASS';state.style.color=s.blocking_criteria?.length?'#ffca8a':'#9ef2e3';
 const meta=document.createElement('small');meta.textContent=(s.metrics?.min_soc_pct??'—')+'% min SOC';card.append(label,state,meta);results.appendChild(card)}
 const body=$('checkRows');body.replaceChildren();for(const s of data.scenarios)for(const c of s.checks||[]){const tr=document.createElement('tr');
 for(const v of [s.key,c.id,c.status+' · '+c.observed+' / '+c.threshold]){const td=document.createElement('td');td.textContent=v;tr.appendChild(td)}body.appendChild(tr)}
 $('checksTable').classList.remove('hidden');['briefDownload','dossierDownload'].forEach(id=>$(id).disabled=false)}
async function runReview(){safeMessage('Recomputing NASA-derived mission scenarios…');busy('runReview',true);try{
 latestReview=await api('mission-review',{method:'POST',body:reviewInput()});renderReview(latestReview);safeMessage('Decision review computed from the current mission parameters.');
 }catch(e){latestReview=null;clearReview();safeMessage('Review failed: '+e.message,true)}finally{busy('runReview',false)}}
async function exportReport(kind){if(!latestReview)return;try{
 const payload=await api('mission-decision/'+kind+'.pdf',{method:'POST',body:reviewInput(),blob:true});
 const link=document.createElement('a'),url=URL.createObjectURL(payload);link.href=url;link.download='POLARIS_'+kind+'_'+latestReview.review_id+'.pdf';
 document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 safeMessage('Private engineering report generated and downloaded.');
 }catch(e){safeMessage('Private report export unavailable: '+e.message,true)}}
function stopHeartbeat(){if(heartbeat){clearInterval(heartbeat);heartbeat=null}}
function closeRealtime(){stopHeartbeat();if(liveSocket){liveSocket.onclose=null;liveSocket.close();liveSocket=null}}
function realtimeLabel(online){const x=$('realtimeStatus');x.classList.toggle('connected',online);x.querySelector('span').textContent=online?'LIVE · SYNCHRONIZED':'LIVE SYNC RECONNECTING'}
function startRealtime(){closeRealtime();if(!identity?.user_id||!session?.access_token||signingOut)return;
 const target=config.supabase_url.replace(/^http/,'ws')+urls.realtime+'?apikey='+encodeURIComponent(config.publishable_key)+'&vsn=1.0.0';
 try{const ws=new WebSocket(target);liveSocket=ws;let ref=1;const topic='realtime:polaris_missions_'+identity.user_id;
 const send=(event,payload)=>{if(ws.readyState===WebSocket.OPEN)ws.send(JSON.stringify({topic,event,payload,ref:String(ref++)}))};
 ws.onopen=()=>{send('phx_join',{config:{postgres_changes:[{event:'*',schema:'public',table:'mission_plans',filter:'owner_id=eq.'+identity.user_id}]},access_token:session.access_token});
  stopHeartbeat();heartbeat=setInterval(()=>send('heartbeat',{}),25000)};
 ws.onmessage=e=>{try{const p=JSON.parse(e.data);if(p.event==='phx_reply'&&p.topic===topic){if(p.payload?.status==='ok'){reconnectAttempt=0;realtimeLabel(true)}else realtimeLabel(false)}
  if(p.event==='postgres_changes'||p.event==='INSERT'||p.event==='UPDATE')loadMissions()}catch(_){}};
 ws.onclose=()=>{stopHeartbeat();realtimeLabel(false);if(liveSocket===ws&&session&&!signingOut){liveSocket=null;const delay=Math.min(30000,1000*(2**Math.min(5,reconnectAttempt++)));setTimeout(()=>{if(session&&!liveSocket)startRealtime()},delay)}};
 ws.onerror=()=>realtimeLabel(false);
 }catch(_){realtimeLabel(false)}}
$('showSignin').addEventListener('click',()=>accessTab('signin'));
$('showSignup').addEventListener('click',()=>accessTab('signup'));
$('signupForm').addEventListener('submit',register);
$('refreshApproval').addEventListener('click',refreshApproval);
$('proceedMfa').addEventListener('click',beginMfa);
$('pendingLogout').addEventListener('click',logout);
$('loginForm').addEventListener('submit',login);$('mfaForm').addEventListener('submit',verifyMfa);
$('cancelMfa').addEventListener('click',()=>{clearState();safeMessage('Authentication cancelled.')});
$('logout').addEventListener('click',logout);$('newMission').addEventListener('click',newMission);
$('missionForm').addEventListener('submit',saveMission);$('runReview').addEventListener('click',runReview);
$('briefDownload').addEventListener('click',()=>exportReport('brief'));$('dossierDownload').addEventListener('click',()=>exportReport('dossier'));
['site','focus','start','delay','pv','load','battery','minSoc','missionTitle'].forEach(id=>$(id).addEventListener('input',()=>{latestReview=null;clearReview()}));
init();
})();
