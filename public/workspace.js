/* POLARIS — Authenticated mission workspace. No credentials in localStorage. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
let config=null, session=null, identity=null, pendingFactor=null, challengeId=null,
    activeId=null,liveSocket=null, heartbeat=null, latestReview=null, reconnectAttempt=0,signingOut=false,pendingTimer=null;
const urls={auth:'/auth/v1',realtime:'/realtime/v1/websocket'};
const safeMessage=(message,error=false)=>{$('message').textContent=message;$('message').className='status'+(error?' error':'')};
function view(name){['loginSection','registerSection','pendingSection','mfaSection','workspaceSection'].forEach(x=>$(x).classList.toggle('hidden',x!==name));document.body.dataset.screen=name;$('intro').classList.add('hidden');$('sessionState').classList.toggle('hidden',name!=='workspaceSection')}
function busy(id,val){$(id).disabled=val}
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
async function init(){view('loginSection');try{
 const r=await fetch('/api/workspace-config',{cache:'no-store'});config=await r.json();
 if(!config.available)throw Error('The workspace requires a POLARIS Supabase connection. The public demonstration remains available.');
 view('loginSection');safeMessage('');
 }catch(e){safeMessage(e.message,true)}}
const TERMS_VERSION='polaris-2026-11-14';
function stopPendingPoll(){if(pendingTimer){clearInterval(pendingTimer);pendingTimer=null}}
async function signup(e){e.preventDefault();busy('registerBtn',true);try{
 const given_name=$('givenName').value.trim(),family_name=$('familyName').value.trim(),employee_id=$('employeeId').value.trim();
 const password=$('signupPassword').value,confirm=$('signupConfirm').value;
 if(!/^[A-Za-z0-9][A-Za-z0-9._-]{2,31}$/.test(employee_id))throw Error('Invalid professional ID.');
 if(password.length<12||password!==confirm)throw Error('Passwords must match and contain at least twelve characters.');
 if(!$('termsAccept').checked)throw Error('Terms acceptance is required.');
 const payload={email:$('signupEmail').value.trim(),password,data:{first_name:given_name,last_name:family_name,staff_id:employee_id,
     accepted_terms:true,terms_version:TERMS_VERSION,polaris_signup:true}};
 const created=await authCall('/signup',{method:'POST',body:payload,token:null});
 $('signupPassword').value='';$('signupConfirm').value='';
 if(created.access_token){session=created;await refreshRequestStatus();}
 else {view('pendingSection');showStatusBadge('pending');$('requestInfo').textContent='Request submitted. Verify your email using the confirmation message, then sign in to check its status.';}
 safeMessage('Registration received. Access depends on review and email confirmation.');
 }catch(e){safeMessage('Registration: '+e.message,true)}finally{busy('registerBtn',false)}}
function showStatusBadge(status){const badge=$('approvalBadge');badge.className='approval-badge '+status;badge.textContent=status.toUpperCase();}
async function refreshRequestStatus(){if(!session?.access_token){showStatusBadge('pending');return}
 const r=await fetch('/api/registration/status',{cache:'no-store',headers:{Authorization:'Bearer '+session.access_token}});
 const result=await r.json().catch(()=>({}));if(!r.ok)throw Error(result.detail||'Registration status unavailable');
 showStatusBadge(result.status);view('pendingSection');
 $('requestInfo').textContent=result.status==='approved'?'Access approved. Complete your sign-in verification.':
    result.status==='rejected'?'Request not approved. Contact the project owner for further information.':
    'Pending review. You can check your status after signing in.';
 stopPendingPoll();
 if(result.status==='approved'){stopPendingPoll();await startMfaForApproved();return}
 if(result.status==='pending'){pendingTimer=setInterval(()=>{if(session)refreshRequestStatus().catch(()=>{});},20000)}
}
async function startMfaForApproved(){stopPendingPoll();
 const factorState=await authCall('/factors');const candidates=(factorState?.totp||[]).filter(x=>x.status==='verified');
 if(candidates.length){pendingFactor=candidates[0].id;await startChallenge();}
 else{const enrol=await authCall('/factors',{method:'POST',body:{factor_type:'totp',friendly_name:'POLARIS Mission Workspace'}});
 pendingFactor=enrol.id;$('enrolPane').classList.remove('hidden');
 const qr=enrol.totp?.qr_code||'';
 if(!qr.startsWith('data:image/svg+xml')&&!qr.startsWith('data:image/png'))throw Error('Authenticator QR code unavailable');
 $('mfaQr').src=qr;await startChallenge();}
}
async function login(e){e.preventDefault();busy('loginBtn',true);safeMessage('Verifying credentials…');try{
 const result=await authCall('/token?grant_type=password',{method:'POST',body:{email:$('email').value.trim(),password:$('password').value}});
 session=result;$('password').value='';
 // Read verified current request before offering multifactor access.
 await refreshRequestStatus();
 }catch(e){session=null;safeMessage('Sign-in failed: '+e.message,true)}finally{busy('loginBtn',false)}}
async function startChallenge(){const q=await authCall('/factors/'+encodeURIComponent(pendingFactor)+'/challenge',{method:'POST',body:{}});
 challengeId=q.id;view('mfaSection');$('totp').value='';$('totp').focus();safeMessage('Enter the fresh six-digit code from your authenticator app.')}
async function verifyMfa(e){e.preventDefault();try{
 const code=$('totp').value.trim();if(!/^\d{6}$/.test(code))throw Error('Enter exactly six digits.');
 const out=await authCall('/factors/'+encodeURIComponent(pendingFactor)+'/verify',{method:'POST',body:{challenge_id:challengeId,code}});
 if(!out.access_token)throw Error('Authenticator did not return a verified session');
 session={...session,...out};$('totp').value='';$('mfaQr').removeAttribute('src');$('enrolPane').classList.add('hidden');
 const account=await api('whoami');identity=account;
 const move=await api('continue',{method:'POST'});
 if(typeof move.next==='string'&&move.next.startsWith('/')){window.location.assign(move.next);return;}
 $('operatorLabel').textContent='Authenticated: '+account.name+'  ·  '+account.role.toUpperCase();
 $('sessionState').textContent='MFA VERIFIED';$('logout').classList.remove('hidden');view('workspaceSection');
 safeMessage('Identity verified. Your mission workspace is isolated by database access policies.');await loadMissions();startRealtime();
 }catch(e){safeMessage('MFA verification: '+e.message,true)}}
function clearState(){stopPendingPoll();session=null;identity=null;activeId=null;latestReview=null;pendingFactor=null;challengeId=null;
 closeRealtime();$('sessionState').textContent='SIGN IN REQUIRED';$('logout').classList.add('hidden');view('loginSection')}
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
$('loginForm').addEventListener('submit',login);$('registerForm').addEventListener('submit',signup);
$('showRegister').addEventListener('click',()=>{view('registerSection');safeMessage('Complete the access request form.');});
$('backToSignIn').addEventListener('click',()=>{view('loginSection');safeMessage('Sign in using an existing account.');});
$('refreshStatus').addEventListener('click',()=>refreshRequestStatus().catch(e=>safeMessage(e.message,true)));
$('pendingSignOut').addEventListener('click',logout);$('mfaForm').addEventListener('submit',verifyMfa);
$('cancelMfa').addEventListener('click',()=>{clearState();safeMessage('Authentication cancelled.')});
$('logout').addEventListener('click',logout);$('newMission').addEventListener('click',newMission);
$('missionForm').addEventListener('submit',saveMission);$('runReview').addEventListener('click',runReview);
$('briefDownload').addEventListener('click',()=>exportReport('brief'));$('dossierDownload').addEventListener('click',()=>exportReport('dossier'));
['site','focus','start','delay','pv','load','battery','minSoc','missionTitle'].forEach(id=>$(id).addEventListener('input',()=>{latestReview=null;clearReview()}));
init();
})();
