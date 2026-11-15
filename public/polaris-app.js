(() => {
'use strict';
const el = id => document.getElementById(id);
const state={site:'connecting_ridge',reference:null,skyline:null,decision:null,index:0,busy:false};
const safe = x => String(x==null?'—':x);
const n = (x,d=1) => Number.isFinite(Number(x)) ? Number(x).toFixed(d) : '—';
const dateLabel=s=>{const d=new Date(s);return d.toLocaleString('en-GB',{timeZone:'UTC',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hour12:false})+' UTC'};
function message(s,error=false){el('liveMsg').textContent=error?'Check error panel for details.':s;el('toast').textContent=error?s:'';el('toast').classList.toggle('show',error)}
function setBusy(b){state.busy=b;el('run').disabled=b;el('replan').disabled=b;el('run').textContent=b?'LOADING NASA DATA…':'↗   RUN NASA MISSION ANALYSIS';el('replan').textContent=b?'WORKING…':'⇄   RUN COUNTERFACTUAL LAB'}
function getInputs(){return new URLSearchParams({site:state.site,start:el('landing').value,delay:el('shift').value,hours:'24',area:el('area').value,load:el('load').value,battery:el('battery').value,mode:el('orientation').value})}
function selected(){for(const key of ['connecting_ridge','shackleton_rim']){const b=el('site-'+key);b.classList.toggle('on',state.site===key);b.setAttribute('aria-pressed',String(state.site===key))}}
async function json(url){const r=await fetch(url);let d;try{d=await r.json()}catch(_){throw Error('Server returned unreadable data ('+r.status+')')}if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Request failed ('+r.status+')');return d}
function download(name,data){const b=new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),a=document.createElement('a');const u=URL.createObjectURL(b);a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1500)}
function formatMetric(x,unit){return '<span class="mission-metric-number">0</span> <i>'+unit+'</i>'}
function renderMetrics(){const o=state.reference;if(!o)return;const s=o.summary;el('metricSun').innerHTML=formatMetric(s.sun_visible_pct,'%');el('metricEarth').innerHTML=formatMetric(s.earth_visible_pct,'%');el('metricGap').innerHTML=formatMetric(s.max_earth_gap_hours,'h');el('metricSoc').innerHTML=formatMetric(s.min_soc_pct,'%');el('metricSunNote').textContent=n(s.sun_visible_hours,0)+' h potentially sunlit / '+n(s.duration_hours,0)+' h';el('metricEarthNote').textContent=n(s.earth_visible_hours,0)+' h local upper bound; NOT a radio link';for(const [id,v,d] of [['metricSun',s.sun_visible_pct,1],['metricEarth',s.earth_visible_pct,1],['metricGap',s.max_earth_gap_hours,0],['metricSoc',s.min_soc_pct,1]])polarisCount(el(id).querySelector('.mission-metric-number'),v,'',d);}
function skyPoint(az,elev,cx=310,cy=242){const ang=(az-90)*Math.PI/180,r=Math.max(38,Math.min(201,145-elev*7));return [cx+Math.cos(ang)*r,cy+Math.sin(ang)*r]}
function skylinePath(arr){return arr.map((v,i)=>{const [x,y]=skyPoint(i*5,v);return(x.toFixed(2)+','+y.toFixed(2))}).join(' ')}
function trackPath(rows,azKey,elKey){return rows.map(r=>{const [x,y]=skyPoint(r[azKey],r[elKey]);return x.toFixed(2)+','+y.toFixed(2)}).join(' ')}
function renderSky(){const ref=state.reference,sky=state.skyline;if(!ref||!sky)return;const rows=ref.samples;const p=rows[state.index]||rows[0];const [sx,sy]=skyPoint(p.sun_az,p.sun_el);const [ex,ey]=skyPoint(p.earth_az,p.earth_el);const horizon=skylinePath(sky.profile.elevations_deg);let svg='';
for(const r of [70,145,190])svg+='<circle cx="310" cy="242" r="'+r+'" fill="none" stroke="#9fe5ec" stroke-width=".8" opacity=".28"/>';
for(let angle=0;angle<360;angle+=30){const [x1,y1]=skyPoint(angle,8),[x2,y2]=skyPoint(angle,-7);svg+='<line x1="'+x1.toFixed(2)+'" y1="'+y1.toFixed(2)+'" x2="'+x2.toFixed(2)+'" y2="'+y2.toFixed(2)+'" stroke="#b9e2e7" opacity=".14"/>'}
for(const [txt,x,y] of [['N',309,16],['S',309,455],['W',55,246],['E',559,246]])svg+='<text x="'+x+'" y="'+y+'" text-anchor="middle">'+txt+'</text>';
svg+='<polyline points="'+horizon+'" stroke="#b0cad3" opacity=".88" fill="none" stroke-width="2.2" stroke-linejoin="round"/>';
svg+='<polyline points="'+trackPath(rows,'sun_az','sun_el')+'" stroke="#ffc78a" stroke-width="2" opacity=".6" fill="none"/>';
svg+='<polyline points="'+trackPath(rows,'earth_az','earth_el')+'" stroke="#72ebeb" stroke-width="2" opacity=".72" fill="none"/>';
svg+='<circle cx="'+sx+'" cy="'+sy+'" r="20" fill="#ffbd7888" opacity=".20"/><circle cx="'+sx+'" cy="'+sy+'" r="7" fill="#ffca91" stroke="#fff3dd" stroke-width="2"/><text x="'+(sx+14)+'" y="'+(sy-9)+'" fill="#ffd8ac">SUN</text>';
svg+='<circle cx="'+ex+'" cy="'+ey+'" r="18" fill="#64e8f088" opacity=".2"/><circle cx="'+ex+'" cy="'+ey+'" r="7" fill="#6deeee" stroke="#d4ffff" stroke-width="2"/><text x="'+(ex+14)+'" y="'+(ey+12)+'">EARTH</text>';
svg+='<circle cx="310" cy="242" r="4" fill="#f7ffff"/><circle cx="310" cy="242" r="12" fill="none" stroke="#77e8e8" stroke-width="1" opacity=".4"/>';
el('skySvg').innerHTML=svg;el('skyAz').textContent='AZIMUTH 0° NORTH · 90° EAST';
el('utcStamp').textContent=dateLabel(p.utc).toUpperCase();el('sunElevation').innerHTML=n(p.sun_el,2)+' <span>deg</span>';el('earthElevation').innerHTML=n(p.earth_el,2)+' <span>deg</span>';el('sunDetail').textContent='Local skyline: '+n(p.sun_horizon_deg,2)+'° · margin '+n(p.sun_margin_deg,2)+'°';el('earthDetail').textContent='Local skyline: '+n(p.earth_horizon_deg,2)+'° · margin '+n(p.earth_margin_deg,2)+'°';el('sunBar').style.width=Math.min(100,Math.max(0,(p.sun_margin_deg+8)/16*100))+'%';el('earthBar').style.width=Math.min(100,Math.max(0,(p.earth_margin_deg+8)/16*100))+'%';
el('sampleDetails').innerHTML=[['UTC sample',dateLabel(p.utc)],['Sun azimuth',n(p.sun_az,2)+'°'],['Sun above local terrain?',p.sun_visible?'POTENTIALLY':'NO'],['Earth azimuth',n(p.earth_az,2)+'°'],['Earth above local terrain?',p.earth_visible?'POTENTIALLY':'NO'],['Battery SOC (illustrative)',n(p.soc*100,1)+'%']].map(([k,v])=>'<div class="keyrow"><span>'+k+'</span><b>'+v+'</b></div>').join('');
el('interpretation').innerHTML=p.earth_visible?'<strong>Potential geometric visibility.</strong> Earth clears the 6-km local skyline at this observation; more distant hills could still block it.':'<strong>Locally obscured.</strong> The Earth is below the 6-km terrain skyline in this sampled direction. This does not model relays.';
}
function svgTime(){const o=state.reference;if(!o)return;const rows=o.samples,w=940,h=245,L=42,R=15,T=16,B=30;const X=i=>L+i/(rows.length-1)*(w-L-R);const Y=y=>T+(12-y)/24*(h-T-B);
const line=(k)=>rows.map((v,i)=>(i?'L':'M')+X(i).toFixed(1)+' '+Y(v[k]).toFixed(1)).join(' ');let result='';for(let y=-8;y<=12;y+=4){result+='<line x1="'+L+'" x2="'+(w-R)+'" y1="'+Y(y)+'" y2="'+Y(y)+'" stroke="#254655" stroke-width="1"/><text x="'+(L-8)+'" y="'+(Y(y)+4)+'" text-anchor="end" fill="#8aa7b7" font-size="11">'+y+'°</text>'}for(let i=0;i<rows.length;i+=4)result+='<text x="'+X(i)+'" y="'+(h-4)+'" text-anchor="middle" fill="#97b8c7" font-size="11">'+(i*6)+'h</text>';
result+='<path d="'+line('sun_el')+'" stroke="#f4c57a" stroke-width="2.7" fill="none"/><path d="'+line('earth_el')+'" stroke="#77e8e8" stroke-width="2.7" fill="none"/><path d="'+line('earth_horizon_deg')+'" stroke="#91aabd" stroke-width="1.8" stroke-dasharray="5 4" fill="none"/><line x1="'+X(state.index)+'" x2="'+X(state.index)+'" y1="'+T+'" y2="'+(h-B)+'" stroke="#dcffff" opacity=".6" stroke-dasharray="3 4"/>';
el('timeChart').setAttribute('viewBox','0 0 '+w+' '+h);el('timeChart').innerHTML=result;}
async function loadReference(){if(state.busy)return;setBusy(true);message('Fetching NASA reference observations…');try{const params=new URLSearchParams({area:el('area').value,load:el('load').value,battery:el('battery').value,mode:el('orientation').value});const [ref,sky]=await Promise.all([json('/api/nasa-reference/'+state.site+'?'+params),json('/api/skyline/'+state.site)]);state.reference=ref;state.skyline=sky;state.index=0;el('timeScrub').value='0';el('skySiteName').textContent=ref.site.name+' · '+n(ref.site.lat_deg,3)+'° lat';selected();renderMetrics();renderSky();svgTime();message('Real NASA ephemerides and 6-km LOLA skyline loaded.')}catch(e){message(e.message,true)}finally{setBusy(false)}}
function renderDecision(d){state.decision=d;el('exportDecision').disabled=false;const scen=[['BASELINE',d.scenarios.original],['DELAYED · SAME POINT',d.scenarios.delayed],['DELAYED · OTHER POINT',d.scenarios.alternative_site_after_delay]];el('scenarioTiles').innerHTML=scen.map(([lab,x])=>'<div class="scenario"><p>'+lab+'</p><h3>'+x.site_name.split('/')[0]+'</h3><p>Potential local Earth clear</p><strong class="highlight">'+n(x.summary.earth_visible_hours,0)+' h</strong><p style="margin-top:7px">Min battery SOC '+n(x.summary.min_soc_pct,1)+' %</p><p>Unserved energy '+n(x.summary.unserved_energy_kwh,2)+' kWh</p></div>').join('');const diff=d.changes.site_change_at_delayed_time;el('decisionVerdict').innerHTML='<i>⇄</i><span>Changing observation point after delay changes the sampled local Earth-clear duration by <strong>'+n(diff.earth_visible_hours,0)+' hours</strong>. A larger value does not prove real radio contact. Far terrain, link budget and landing hazards are unmodeled.</span>'}
async function runDecision(){if(state.busy)return;setBusy(true);message('Recomputing three comparable missions…');try{const d=await json('/api/replan?'+getInputs());renderDecision(d);message('Replanning completed. Results are 6-hour sample estimates.');location.hash='#/scenarios'}catch(e){message(e.message,true)}finally{setBusy(false)}}
function makeAtlas(layer){const l=layer==='earth'?'AVGVISIB_85S_060M_201608_EARTH_SP':'WAC_POLE_ILL_PCT_SOUTH_100M',tile=el('maptiles');tile.replaceChildren();for(const row of [15,16])for(const col of [15,16]){let im=new Image();im.alt='';im.loading='lazy';im.decoding='async';im.src='https://trek.nasa.gov/tiles/Moon/SP/'+l+'/1.0.0/default/default028mm/5/'+row+'/'+col+'.png';im.onerror=()=>{el('mapStatus').textContent='Moon Trek map tiles are unavailable in this browser. Open the NASA source through the Moon Trek link.'};tile.appendChild(im)}el('mapStatus').textContent='NASA Moon Trek WMTS · aggregated '+(layer==='earth'?'Earth visibility':'illumination')+' map (NOT mission-date conditions).';for(const [id,v] of [['mapSun','sun'],['mapEarth','earth']]){el(id).classList.toggle('active',v===layer);el(id).setAttribute('aria-pressed',String(v===layer))}}
for(const key of ['connecting_ridge','shackleton_rim'])el('site-'+key).addEventListener('click',()=>{state.site=key;selected();loadReference()});
for(const id of ['area','load'])el(id).addEventListener('input',()=>{el(id+'Val').textContent=el(id).value+(id==='area'?' m²':' W')});
el('run').addEventListener('click',loadReference);el('replan').addEventListener('click',runDecision);el('timeScrub').addEventListener('input',()=>{state.index=Number(el('timeScrub').value);renderSky();svgTime()});el('exportDecision').addEventListener('click',()=>state.decision&&download('polaris-mission-counterfactual.json',state.decision));el('downloadSample').addEventListener('click',()=>state.reference&&download('polaris-reference-'+state.site+'.json',state.reference));el('mapSun').addEventListener('click',()=>makeAtlas('sun'));el('mapEarth').addEventListener('click',()=>makeAtlas('earth'));
for(const x of document.querySelectorAll('.railnav a'))x.addEventListener('click',()=>{document.querySelectorAll('.railnav a').forEach(e=>e.classList.remove('current'));x.classList.add('current')});

// Mission mesh: source-first interaction inspired by dataflow storytelling,
// original implementation, without copied artwork/code from badluxus.dev.
const meshNodes=[
 {label:'01 / SOURCE INGESTION',title:'JPL Horizons ephemerides',description:'NASA/JPL provides apparent Sun and Earth positions for the selected lunar observer. Angular geometry is an input, not a completed mission assessment.',code:'JPL → UTC / AZ / EL',caution:'NO DIRECT TERRAIN OR RADIO PREDICTION',value:()=>state.reference?state.reference.samples.length+' epochs':'—',unit:'sampled positions'},
 {label:'02 / SURFACE GEOMETRY',title:'NASA LOLA topographic skyline',description:'A 5 m/pixel LOLA DEM establishes local horizon obstruction around the observer. Mountains beyond the 6 km sampled radius remain unknown.',code:'LOLA DEM → HORIZON(az)',caution:'DISTANT TERRAIN UNMODELED',value:()=>state.skyline?state.skyline.radius_km+' km':'6 km',unit:'local ray limit'},
 {label:'03 / ENERGY MODEL',title:'Illustrative power survival envelope',description:'The solar and battery model translates sampled visibility into an illustrative state of charge for user-specified PV area, load and storage.',code:'PV × SOLAR → SOC',caution:'SIMPLIFIED POWER MODEL · NOT CERTIFIED',value:()=>state.reference?n(state.reference.summary.min_soc_pct,1)+'%':'—',unit:'minimum battery SOC'},
 {label:'04 / DECISION EXPLORER',title:'What if the mission is delayed?',description:'Compare the initial 24-hour period with a delayed mission at the same point and a different point. The calculation preserves assumptions but does not rank site safety.',code:'BASELINE → DELAY → ALT',caution:'NO UNIVERSAL BEST-SITE SCORE',value:()=>state.decision?String(Object.keys(state.decision.scenarios||{}).length):'3',unit:'mission scenarios'},
 {label:'05 / SCIENTIFIC EVIDENCE',title:'SPICE cross-check and cadence audit',description:'228 SPICE-versus-Horizons angular comparisons check algorithmic consistency. A separate audit demonstrates a three-hour Earth-visibility difference between 6-hour and 1-hour sampling.',code:'SPICE / HORIZONS → QA',caution:'6 KM & 6 H LIMITS STILL APPLY',value:()=> '228',unit:'cross-check comparisons'}
];
let meshIdx=0,meshTimer=null,orbitTimer=null,cmdPrevFocus=null;
function meshSelect(idx){idx=(idx+meshNodes.length)%meshNodes.length;meshIdx=idx;const m=meshNodes[idx];document.querySelectorAll('[data-mesh]').forEach(x=>{let yes=Number(x.dataset.mesh)===idx;x.classList.toggle('active',yes);x.setAttribute('aria-pressed',String(yes))});el('meshLabel').textContent=m.label;el('meshNodeTitle').textContent=m.title;el('meshDescription').textContent=m.description;el('meshSignal').textContent=m.code+' · '+(state.site==='connecting_ridge'?'CONNECTING RIDGE':'SHACKLETON RIM');el('meshCaution').textContent=m.caution;el('meshMetricLabel').textContent=m.unit.toUpperCase();el('meshMetric').textContent=m.value()}
function meshStop(){if(meshTimer){clearInterval(meshTimer);meshTimer=null}el('meshAuto').textContent='▶ TRACE MISSION FLOW';el('meshAuto').setAttribute('aria-pressed','false')}
function meshPlay(){if(meshTimer){meshStop();return}meshSelect(0);el('meshAuto').textContent='■ STOP TRACE';el('meshAuto').setAttribute('aria-pressed','true');let k=0;meshTimer=setInterval(()=>{k+=1;if(k>=meshNodes.length){meshStop();return}meshSelect(k)},2200)}
for(const button of document.querySelectorAll('[data-mesh]'))button.addEventListener('click',()=>{meshStop();meshSelect(Number(button.dataset.mesh))});
el('meshAuto').addEventListener('click',meshPlay);
el('startTourTop').addEventListener('click',()=>{el('missionFlow').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'});meshPlay()});
if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches){el('meshGraph').addEventListener('pointermove',ev=>{const r=el('meshGraph').getBoundingClientRect();const x=(ev.clientX-r.left)/r.width,y=(ev.clientY-r.top)/r.height;el('missionFlow').style.setProperty('--fx',(x*100).toFixed(1)+'%');el('missionFlow').style.setProperty('--fy',(y*100).toFixed(1)+'%')},{passive:true})}
function stopOrbit(){if(orbitTimer){clearInterval(orbitTimer);orbitTimer=null}el('orbitReplay').textContent='▶ REPLAY OBSERVATIONS';el('orbitReplay').setAttribute('aria-pressed','false')}
function orbitPlay(){if(orbitTimer){stopOrbit();return}if(!state.reference)return;el('orbitReplay').textContent='■ STOP REPLAY';el('orbitReplay').setAttribute('aria-pressed','true');state.index=0;el('timeScrub').value='0';renderSky();svgTime();orbitTimer=setInterval(()=>{if(!state.reference || state.index>=state.reference.samples.length-1){stopOrbit();return}state.index++;el('timeScrub').value=String(state.index);renderSky();svgTime()},700)}
el('orbitReplay').addEventListener('click',orbitPlay);el('timeScrub').addEventListener('pointerdown',stopOrbit);
function terminalOpen(){cmdPrevFocus=document.activeElement;el('missionCommand').hidden=false;el('cmdInput').value='';el('cmdInput').focus()}
function terminalClose(){el('missionCommand').hidden=true;if(cmdPrevFocus&&typeof cmdPrevFocus.focus==='function')cmdPrevFocus.focus()}
el('meshConsole').addEventListener('click',terminalOpen);el('cmdClose').addEventListener('click',terminalClose);
el('missionCommand').addEventListener('pointerdown',ev=>{if(ev.target===el('missionCommand'))terminalClose()});
document.addEventListener('keydown',ev=>{
 if(ev.key==='Escape'&&!el('missionCommand').hidden){ev.preventDefault();terminalClose();return}
 if(ev.key==='`'&&!ev.repeat){if(/input|textarea|select/i.test(ev.target.tagName)||ev.target.isContentEditable)return;ev.preventDefault();el('missionCommand').hidden?terminalOpen():terminalClose()}
 if(ev.key==='Tab'&&!el('missionCommand').hidden){const f=[el('cmdClose'),el('cmdInput')];const i=f.indexOf(document.activeElement);if(ev.shiftKey&&i===0){ev.preventDefault();f[1].focus()}else if(!ev.shiftKey&&i===1){ev.preventDefault();f[0].focus()}}
});
function terminalResult(s){el('cmdOutput').textContent=s}
el('cmdForm').addEventListener('submit',async ev=>{
 ev.preventDefault();const t=el('cmdInput').value.trim().toLowerCase().replace(/\s+/g,' '),v=t.split(' ');
 if(t==='help'){terminalResult('COMMANDS / REAL OPERATIONS\nsite ridge · site shackleton\ndelay 24 · delay 48 · delay 72\nobserve · replan · time 0..16\nsources · spice · mesh · clear · close');return}
 if(t==='clear'){terminalResult('POLARIS terminal ready.');return}
 if(t==='close'){terminalClose();return}
 if(t==='site ridge'||t==='site connecting'){state.site='connecting_ridge';selected();terminalResult('Observer set: Connecting Ridge. Fetching NASA reference…');await loadReference();meshSelect(meshIdx);return}
 if(t==='site shackleton'){state.site='shackleton_rim';selected();terminalResult('Observer set: Shackleton Rim. Fetching NASA reference…');await loadReference();meshSelect(meshIdx);return}
 if(v[0]==='delay' && ['24','48','72'].includes(v[1])&&v.length===2){el('shift').value=v[1];terminalResult('Mission delay set to +'+v[1]+' hours. Run replan for three scenarios.');return}
 if(v[0]==='time' && v.length===2 && /^\d+$/.test(v[1])){let index=Number(v[1]);if(state.reference && index<state.reference.samples.length){stopOrbit();state.index=index;el('timeScrub').value=String(index);renderSky();svgTime();terminalResult('Observation: '+state.reference.samples[index].utc+' · sample index '+index);return}}
 if(t==='observe'){terminalResult('Loading NASA observer data…');await loadReference();meshSelect(0);return}
 if(t==='replan'){terminalResult('Running 3 mission scenarios from NASA reference data…');await runDecision();meshSelect(3);terminalResult(state.decision?'Replan complete. See Mission Reschedule Lab for comparisons and limitations.':'Replan unavailable. Inspect the error message in mission controls.');return}
 if(t==='mesh'){terminalClose();location.hash='#/evidence';setTimeout(meshPlay,90);return}
 if(t==='sources'){terminalClose();location.hash='#/atlas';return}
 if(t==='spice'){terminalResult('Opening scientific cross-check source in new tab…');window.open('/api/spice-validation','_blank','noopener');return}
 terminalResult('UNKNOWN COMMAND: '+t+'\nType help for approved commands. Values must remain inside the NASA demo dataset.');
});
// Reduced-motion-aware UI metric count-up; numeric endpoints remain unchanged.
function polarisCount(elm,target,suffix='',digits=0){
 if(!elm||!Number.isFinite(target))return;const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
 if(reduce){elm.textContent=target.toFixed(digits)+suffix;return}
 const current=parseFloat(elm.textContent.replace(/[^\d.\-]/g,''));const start=Number.isFinite(current)?current:0;
 const begin=performance.now(),length=350;function step(t){const u=Math.min(1,(t-begin)/length),e=1-Math.pow(1-u,3);elm.textContent=(start+(target-start)*e).toFixed(digits)+suffix;if(u<1)requestAnimationFrame(step)}requestAnimationFrame(step)
}
// Keep the interactive processing mesh synchronized when API requests complete.
const originalRenderMetrics=renderMetrics;renderMetrics=()=>{originalRenderMetrics();meshSelect(meshIdx)};
const originalRenderDecision=renderDecision;renderDecision=(d)=>{originalRenderDecision(d);meshSelect(meshIdx)};

makeAtlas('sun');loadReference();
/* POLARIS v0.9 — mission multi-view router; seven URL-addressable screens. */
const ROUTES=[
 {id:'mission',title:'MISSION / OVERVIEW',hint:'Choose one NASA lunar observation point and load its mission model.'},
 {id:'sky',title:'SKY / TOPOGRAPHY',hint:'Study Sun and Earth elevations against the local topographic horizon.'},
 {id:'scenarios',title:'SCENARIOS / WHAT-IF',hint:'Select a date, delay and site, then run three comparable missions.'},
 {id:'power',title:'ELECTRICAL / POWER',hint:'Vary PV area, battery capacity and electrical load, then recompute.'},
 {id:'atlas',title:'ATLAS / NASA',hint:'View NASA map layers and explore the source datasets.'},
 {id:'evidence',title:'EVIDENCE / VALIDATION',hint:'Check the model pipeline, numerical cross-checks and uncertainty.'},
 {id:'copilot',title:'COPILOT / DECISION SUPPORT',hint:'Ask a question, configure constraints and calculate a new mission experiment.'},
 {id:'review',title:'DECISION / REVIEW',hint:'Recompute mission constraints and export a scenario-specific engineering decision package.'}
];
function routeId(){const id=location.hash.replace(/^#\/?/,'').split('?')[0]||'mission';return ROUTES.some(x=>x.id===id)?id:'mission'}
function navigateRoute(){const id=routeId(),pos=ROUTES.findIndex(x=>x.id===id);document.body.dataset.view=id;
 document.querySelectorAll('[data-page]').forEach(x=>{x.hidden=x.dataset.page!==id});
 document.querySelectorAll('[data-nav]').forEach(x=>{const selected=x.dataset.nav===id;if(selected)x.setAttribute('aria-current','page');else x.removeAttribute('aria-current')});
 el('currentPageLabel').textContent=ROUTES[pos].title;el('stepProgress').textContent=String(pos+1).padStart(2,'0')+' / 08';
 el('stepExplain').textContent=ROUTES[pos].hint;el('nextPage').textContent=pos===6?'BACK TO MISSION ↗':'NEXT STEP ↗';
 document.title='POLARIS — '+ROUTES[pos].title.replace(' / ',' · ');
 window.scrollTo({top:0,left:0,behavior:'instant'});
 if(id==='power')renderPower();if(id==='scenarios')syncQuickInputs();
}
window.addEventListener('hashchange',navigateRoute);
el('nextPage').addEventListener('click',()=>{const pos=ROUTES.findIndex(x=>x.id===routeId());location.hash='#/'+ROUTES[(pos+1)%ROUTES.length].id});
// Single click in sidebar, no page-length scrolling; browser history and back work.
function syncQuickInputs(){el('qSite').value=state.site;el('qStart').value=el('landing').value;el('qDelay').value=el('shift').value}
for (const id of ['qSite','qStart','qDelay']) el(id).addEventListener('change',()=>{state.site=el('qSite').value;el('landing').value=el('qStart').value;el('shift').value=el('qDelay').value;selected()});
el('qRun').addEventListener('click',async()=>{const b=el('qRun');b.disabled=true;const label=b.textContent;b.textContent='COMPUTING SCENARIOS…';try{state.site=el('qSite').value;el('landing').value=el('qStart').value;el('shift').value=el('qDelay').value;selected();if(!state.reference||state.reference.site_key!==state.site)await loadReference();if(!state.busy)await runDecision()}catch(err){el('liveMsg').textContent='Scenario calculation unavailable: '+err.message}finally{b.disabled=false;b.textContent=label}});
for (const pair of [['powerArea','powerAreaValue',' m²'],['powerLoad','powerLoadValue',' W']]) el(pair[0]).addEventListener('input',()=>{el(pair[1]).textContent=el(pair[0]).value+pair[2]});
function syncPowerInputs(){el('powerArea').value=el('area').value;el('powerLoad').value=el('load').value;el('powerBattery').value=el('battery').value;el('powerMode').value=el('orientation').value;el('powerAreaValue').textContent=el('area').value+' m²';el('powerLoadValue').textContent=el('load').value+' W'}
function renderElectricalBudget(){
 const ref=state.reference;
 if(!ref)return;
 const rows=ref.samples||[];
 const load=Number(el('load').value);
 const energyPvKwh=rows.reduce((sum,row)=>sum+(Number(row.pv_w)||0)*(Number(row.sample_hours)||0)/1000,0);
 const hours=Number(ref.summary?.duration_hours)||0;
 const write=(id,value)=>{const node=el(id);if(node)node.textContent=value};
 write('eeLoad',load.toFixed(0)+' W');
 write('eeDemandDay',(load*24/1000).toFixed(2)+' kWh / day');
 write('eePvEnergy',energyPvKwh.toFixed(2)+' kWh / '+hours.toFixed(0)+' h');
 write('eeLoadEnergy',(load*hours/1000).toFixed(2)+' kWh / '+hours.toFixed(0)+' h');
 write('eeDarkHours',Number(ref.summary.max_dark_hours).toFixed(1)+' h');
 write('eeMinSoc',Number(ref.summary.min_soc_pct).toFixed(1)+' %');
}
function renderPower(){if(!state.reference){el('powerConclusion').textContent='Loading NASA observations. If this persists, open the Mission screen and run the analysis.';return}
 renderElectricalBudget();
 const ref=state.reference,s=ref.summary,rows=ref.samples,plot=el('powerChart');
 el('powerMinSoc').textContent=n(s.min_soc_pct,1)+'%';el('powerDeficit').textContent=n(s.unserved_energy_kwh,2)+' kWh';el('powerFinalSoc').textContent=n(s.last_soc_pct,1)+'%';
 el('powerSiteTitle').textContent=state.site==='connecting_ridge'?'CONNECTING RIDGE':'SHACKLETON RIM';
 const w=800,h=275,L=49,R=22,T=18,B=31;let markup='';const X=i=>L+(w-L-R)*i/Math.max(1,rows.length-1),Y=v=>T+(100-v)*(h-T-B)/100;
 for(let val=0;val<=100;val+=20){markup+='<line x1="'+L+'" x2="'+(w-R)+'" y1="'+Y(val)+'" y2="'+Y(val)+'" stroke="#244552"/><text x="'+(L-8)+'" y="'+(Y(val)+4)+'" fill="#95b9c4" font-size="11" text-anchor="end">'+val+'%</text>'}
 const points=rows.map((r,i)=>(i?'L':'M')+X(i).toFixed(1)+' '+Y(r.soc*100).toFixed(1)).join(' ');
 markup+='<path d="'+points+'" fill="none" stroke="#65f0db" stroke-width="3" stroke-linecap="round"/>';
 markup+='<line x1="'+L+'" x2="'+(w-R)+'" y1="'+Y(20)+'" y2="'+Y(20)+'" stroke="#e3c383" stroke-dasharray="5 5" opacity=".8"/>';
 for(let i=0;i<rows.length;i+=4)markup+='<text x="'+X(i)+'" y="'+(h-7)+'" text-anchor="middle" fill="#90adba" font-size="11">'+(i*6)+'h</text>';
 plot.setAttribute('viewBox','0 0 '+w+' '+h);plot.innerHTML=markup;
 el('powerConclusion').textContent=s.unserved_energy_kwh>0?'Model estimates '+n(s.unserved_energy_kwh,2)+' kWh of unmet demand under these parameters. Revise load, array area or battery storage; this is a non-certified approximation.':'No unserved energy under this simplified model and sampled 6 km horizon. This does not demonstrate actual lunar mission survivability.';
}
el('powerRun').addEventListener('click',async()=>{
 const button=el('powerRun'),label=button.textContent;button.disabled=true;button.textContent='RECOMPUTING POWER…';
 try{
 el('area').value=el('powerArea').value;el('load').value=el('powerLoad').value;el('battery').value=el('powerBattery').value;el('orientation').value=el('powerMode').value;
 el('areaVal').textContent=el('area').value+' m²';el('loadVal').textContent=el('load').value+' W';
 await loadReference();syncPowerInputs();renderPower();
 }catch(err){el('powerConclusion').textContent='Power calculation unavailable: '+err.message}
 finally{button.disabled=false;button.textContent=label}
});
el('powerSwapSite').addEventListener('click',async()=>{state.site=state.site==='connecting_ridge'?'shackleton_rim':'connecting_ridge';selected();await loadReference();renderPower()});
const v08RenderMetrics=renderMetrics;renderMetrics=()=>{v08RenderMetrics();renderPower()};
// Keep the introductory guided tour usable even when Mission Mesh has moved to Evidence.
el('startTourTop').addEventListener('click',ev=>{ev.preventDefault();ev.stopImmediatePropagation();location.hash='#/evidence';setTimeout(()=>meshPlay(),80)},true);
// Original command palette remains; retarget internal jumps to visible routes.
window.addEventListener('hashchange',()=>{if(routeId()!=='mission')stopOrbit()});

function invalidateDecision(){
 state.decision=null;el('exportDecision').disabled=true;
 el('scenarioTiles').innerHTML='<p class="tiny">Mission assumptions changed. Press COMPUTE 3 SCENARIOS to refresh all comparisons.</p>';
 el('decisionVerdict').innerHTML='<i>⇄</i><span>Previous scenario results are stale. Recompute before comparing sites.</span>';
}
for(const cid of ['area','load','battery','orientation','landing','shift','qSite','qStart','qDelay']){
 el(cid).addEventListener('input',invalidateDecision);
 el(cid).addEventListener('change',invalidateDecision);
}
for(const site of ['connecting_ridge','shackleton_rim'])el('site-'+site).addEventListener('click',invalidateDecision,{capture:true});
el('powerRun').addEventListener('click',invalidateDecision,{capture:true});
el('powerSwapSite').addEventListener('click',invalidateDecision,{capture:true});


/* Copilot: no fabricated calculations, backend POST recomputes all scenarios. */
let copilotBusy=false,lastCopilot=null,lastParameterField=null;const copilotHistory=[];
async function loadCopilotStatus(){try{const r=await fetch('/api/copilot/status');const s=await r.json();el('copilotConnection').textContent=s.provider_configured?'OLLAMA CLOUD · CONFIGURED (NOT VERIFIED)':s.setup_required?'OLLAMA CLOUD · SETUP REQUIRED':'ENGINEERING ENGINE · OFFLINE';}catch{el('copilotConnection').textContent='ENGINEERING ENGINE'}}
function coLine(kind,text){const node=document.createElement('div');node.className='chat-line '+kind;if(kind==='bot'){const name=document.createElement('div');name.className='chat-meta';name.textContent='POLARIS / MISSION ANALYSIS';node.append(name)}const body=document.createElement('div');body.textContent=text;node.append(body);el('copilotChat').append(node);node.scrollIntoView({block:'nearest'});return node}
function coBar(num,max){const d=document.createElement('strong');d.textContent=Number(num).toFixed(1);if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches && Number.isFinite(num)){let n=0,t0=performance.now();const tick=(t)=>{const p=Math.min(1,(t-t0)/480);d.textContent=(num*(1-Math.pow(1-p,3))).toFixed(1);if(p<1)requestAnimationFrame(tick)};requestAnimationFrame(tick)}return d}
function coRender(data){const out=el('copilotOutcomes');out.replaceChildren();if(!data.scenarios||!data.scenarios.length){el('copilotProvenance').textContent='No simulation was run. '+(data.flow?.reason||'Clarification or review requested.');return}for(const s of data.scenarios){const card=document.createElement('article');card.className='co-card '+(s.constraints.status==='PASS'?'co-pass':'co-fail');const head=document.createElement('div');head.className='co-section-title';const title=document.createElement('strong');title.textContent=s.id.replaceAll('_',' ').toUpperCase();const badge=document.createElement('span');badge.className='badge '+(s.constraints.status==='PASS'?'good':'amber');badge.textContent=s.constraints.status;head.append(title,badge);card.append(head);const stats=document.createElement('div');stats.className='co-stats';for(const [label,key,unit] of [['MIN SOC','min_soc_pct','%'],['EARTH GEOMETRY','earth_visible_hours',' h'],['ENERGY DEFICIT','unserved_energy_kwh',' kWh']]){const b=document.createElement('div');b.className='co-stat';const caption=document.createElement('small');caption.textContent=label;const value=coBar(Number(s.metrics[key]));b.append(caption,value,document.createTextNode(unit));stats.append(b)}card.append(stats);const rule=document.createElement('p');rule.className='micro';rule.textContent=s.constraints.rules.map(x=>(x.status==='PASS'?'✓ ':'⚠ ')+x.label+': '+x.observed+x.unit+' '+x.op+' '+x.threshold+x.unit).join(' · ');card.append(rule);out.append(card)}
 if(data.what_if){const box=document.createElement('div');box.className='copilot-hint';const text=document.createElement('div');text.textContent='RECALCULATED PROPOSAL: '+data.what_if.label+' — Minimum SOC '+data.what_if.old.min_soc_pct+'% → '+data.what_if.new.min_soc_pct+'%. Unserved energy '+data.what_if.old.unserved_energy_kwh+' → '+data.what_if.new.unserved_energy_kwh+' kWh.';box.append(text);const button=document.createElement('button');button.className='co-apply';button.type='button';button.textContent='APPLY & SIMULATE MISSION ↗';button.setAttribute('aria-label','APPLY THESE PARAMETERS to the live mission and recompute scenarios');button.addEventListener('click',async()=>{for(const [k,v] of Object.entries(data.what_if.changed_inputs)){if(k==='load_w'){el('load').value=v;el('powerLoad').value=v;el('loadVal').textContent=v+' W'}if(k==='battery_kwh'){el('battery').value=v;el('powerBattery').value=v}if(k==='pv_area_m2'){el('area').value=v;el('powerArea').value=v;el('areaVal').textContent=v+' m²'}if(k==='site_key'){state.site=v;selected()}if(k==='delay_hours'){el('shift').value=String(v);el('qDelay').value=String(v)}}syncPowerInputs();invalidateDecision();location.hash='#/scenarios';await loadReference();await runDecision();renderPower()});box.append(button);out.append(box)}
 const provenance=el('copilotProvenance');provenance.replaceChildren();const label=document.createElement('p');label.textContent='Source dataset SHA-256: '+(data.dataset_sha256||'unavailable').slice(0,18)+'… · '+(data.mode==='llm_explainer'?'Language model explanation: '+data.provider+' / '+data.provider_model:'Engineering-calculated analysis; no external LLM needed.');provenance.append(label);for(const e of (data.evidence||[])){const a=document.createElement('a');a.href=e.url;a.target='_blank';a.rel='noopener';a.textContent=e.label+' ↗';provenance.append(a)}
}
async function runCopilot(){if(copilotBusy)return;copilotBusy=true;const button=el('copilotSubmit');button.disabled=true;button.textContent='CALCULATING…';const q=el('copilotQuestion').value.trim();if(q.length<2){copilotBusy=false;button.disabled=false;return}coLine('user',q);el('copilotQuestion').value='';el('copilotFeedback').textContent='Calculating NASA-grounded mission response…';const loading=coLine('bot','Recomputing the mission geometry and constraints…');const payload={question:q,history:copilotHistory.slice(-12),previous_field:lastParameterField,site:state.site,start:el('landing').value||'2026-11-14T00:00Z',duration_hours:24,delay_hours:Number(el('shift').value),pv_area_m2:Number(el('area').value),load_w:Number(el('load').value),battery_kwh:Number(el('battery').value),panel_mode:el('orientation').value,action:el('coAction').value,min_soc_pct:Number(el('coMinSoc').value),min_local_earth_hours:Number(el('coMinEarth').value),max_local_earth_gap_hours:Number(el('coMaxGap').value)};
 try{const response=await fetch('/api/copilot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(45000)});const body=await response.json();if(!response.ok)throw Error(typeof body.detail==='string'?body.detail:'Unable to compute mission');const label=body.mode==='llm_explainer'?'LLM-EXPLAINED + PYTHON-VERIFIED':body.mode==='engineering_fallback'?'ENGINEERING · LLM UNAVAILABLE':'ENGINEERING ANALYSIS';el('copilotMode').textContent=label;loading.querySelector('div:last-child').textContent=body.answer||'Analysis complete. Review the scenario evidence below.';lastCopilot=body;coRender(body);el('copilotFeedback').textContent='Response complete — '+(body.scenarios?.length||0)+' scenarios evaluated. Scroll to the conversation for details.';loading.scrollIntoView({block:'nearest',behavior:'auto'});copilotHistory.push({role:'user',content:q},{role:'assistant',content:body.answer});if(copilotHistory.length>12)copilotHistory.splice(0,copilotHistory.length-12);if(body.flow&&body.flow.updates){const fields=Object.keys(body.flow.updates);if(fields.length===1)lastParameterField=fields[0]}/* LLM explanation is displayed as the answer itself; numerical evidence remains in cards. */}catch(err){loading.querySelector('div:last-child').textContent='Unable to evaluate the mission: '+err.message+' — verify the mission date, delay and numerical thresholds.';el('copilotFeedback').textContent='Analysis failed: '+err.message}finally{button.disabled=false;button.textContent='SEND MESSAGE ↗';copilotBusy=false}}
el('copilotForm').addEventListener('submit',e=>{e.preventDefault();runCopilot()});
function reportPayload(){return {question:el('copilotQuestion').value.trim()||'Generate the current mission simulation report',site:state.site,start:el('landing').value||'2026-11-14T00:00Z',duration_hours:24,delay_hours:Number(el('shift').value),pv_area_m2:Number(el('area').value),load_w:Number(el('load').value),battery_kwh:Number(el('battery').value),panel_mode:el('orientation').value,action:'explain',min_soc_pct:Number(el('coMinSoc').value),min_local_earth_hours:Number(el('coMinEarth').value),max_local_earth_gap_hours:Number(el('coMaxGap').value)}}
async function downloadReport(extension){const id=extension==='pdf'?'coReportPdf':'coReportTex';const button=el(id);button.disabled=true;el('coReportStatus').textContent='Recomputing the mission report…';try{const r=await fetch('/api/mission-report.'+extension,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(reportPayload()),signal:AbortSignal.timeout(27000)});if(!r.ok){let detail=await r.text();try{detail=JSON.parse(detail).detail||detail}catch{}throw Error(String(detail).slice(0,250))}const content=await r.blob();const url=URL.createObjectURL(content),a=document.createElement('a');a.href=url;a.download='POLARIS_'+(r.headers.get('X-POLARIS-REPORT-ID')||'mission')+'.'+extension;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);el('coReportStatus').textContent='Report file prepared and browser download requested: '+a.download}catch(err){el('coReportStatus').textContent='Report unavailable: '+err.message}finally{button.disabled=false}}
el('coReportPdf').addEventListener('click',()=>downloadReport('pdf'));el('coReportTex').addEventListener('click',()=>downloadReport('tex'));

el('copilotQuestion').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();el('copilotForm').requestSubmit()}});loadCopilotStatus();
el('coJumpScenarios').addEventListener('click',()=>location.hash='#/scenarios');


/* Mission Decision Review: computed-only, always bound to the active mission. */
let latestReview=null,reviewBusy=false;
function reviewPayload(){const p=reportPayload();return {...p,focus:el('reviewFocus').value,
  selected_scenarios:[...document.querySelectorAll('input[name="scenario"]:checked')].map(n=>n.value),
  include_trace:el('reviewTrace').checked,include_events:el('reviewEvents').checked,
  mission_label:el('reviewLabel').value.trim(),min_soc_pct:Number(el('reviewMinSoc').value),
  min_local_earth_hours:Number(el('reviewMinEarth').value),max_local_earth_gap_hours:Number(el('reviewMaxGap').value)};}
function numberRise(node,end){if(!node)return;const value=Number(end)||0;
 if(matchMedia('(prefers-reduced-motion:reduce)').matches){node.textContent=String(value);return}
 let start=performance.now();const update=t=>{const z=Math.min(1,(t-start)/450);node.textContent=String(Math.round(value*(1-Math.pow(1-z,3))));if(z<1)requestAnimationFrame(update)};requestAnimationFrame(update)}
function markReviewStale(){if(!latestReview)return;latestReview=null;el('reviewStatus').textContent='Mission parameters changed. Recompute the review to refresh the decision.';
 for(const b of document.querySelectorAll('[data-review-download]'))b.disabled=true;el('reviewId').textContent='STALE RUN'}
function reviewBlock(text,cls){const div=document.createElement('div');div.className=cls||'';div.textContent=text;return div}
function renderDecisionReview(d){if(!Array.isArray(d.scenarios)||!Array.isArray(d.blocking_criteria))throw Error('Unexpected mission review response');latestReview=d;el('reviewId').textContent=d.review_id;el('reviewStatus').textContent=d.status+' — '+d.analysis_scope;
 numberRise(el('reviewScenarioCount'),d.scenarios.length);numberRise(el('reviewBlockerCount'),d.blocking_criteria.length);numberRise(el('reviewEventCount'),d.total_detected_events);
 const target=el('reviewResults');target.replaceChildren();
 for(const sc of d.scenarios){const card=document.createElement('article');card.className='review-run-card';
 const header=document.createElement('div');header.className='review-run-head';
 const name=document.createElement('strong');name.textContent=sc.label+' / '+sc.site.split(' / ')[0];
 const status=document.createElement('em');status.className=sc.blocking_criteria.length?'is-fail':'';status.textContent=sc.decision;header.append(name,status);card.append(header);
 const sub=reviewBlock('UTC '+sc.start_utc+' • '+sc.checks.length+' criteria evaluated • '+sc.event_count+' detected events');sub.className='review-muted';card.append(sub);
 const grid=document.createElement('div');grid.className='review-rules';for(const r of sc.checks){
  const left=document.createElement('span');left.textContent=r.label+' ('+r.op+' '+r.threshold+' '+r.unit+')';
  const right=document.createElement('span');right.textContent=(Number.isFinite(Number(r.observed))?Number(r.observed).toFixed(2):String(r.observed))+' '+r.unit+' · '+r.status;
  right.style.color=r.status==='FAIL'?'#ffbf8a':'#8beddd';grid.append(left,right)}card.append(grid);
 if(sc.events.length){const ev=document.createElement('div');ev.className='review-events';for(const item of sc.events.slice(0,7)){
 const p=document.createElement('p');p.textContent=item.description;ev.append(p)}card.append(ev)}target.append(card)}
 for(const b of document.querySelectorAll('[data-review-download]'))b.disabled=false;
 el('reviewDownloadStatus').textContent='Decision package ready: '+d.review_id+' • '+d.selected_scenarios.length+' selected scenarios.'}
async function computeDecisionReview(e){if(e)e.preventDefault();if(reviewBusy)return;
 const req=reviewPayload();if(!req.selected_scenarios.length){el('reviewStatus').textContent='Select at least one scenario.';return}
 reviewBusy=true;el('reviewCompute').disabled=true;el('reviewCompute').textContent='RECOMPUTING NASA SIMULATIONS…';
 el('reviewStatus').textContent='Calculating current mission and verifying engineer-selected thresholds…';
 try{const r=await fetch('/api/mission-review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(req),signal:AbortSignal.timeout(28000)});
 const body=await r.json();if(!r.ok)throw Error(typeof body.detail==='string'?body.detail:'Unable to compute decision');renderDecisionReview(body);el('reviewStatus').scrollIntoView({block:'nearest',behavior:'auto'})}
 catch(err){latestReview=null;el('reviewId').textContent='ERROR';el('reviewStatus').textContent='Review failed: '+err.message+' — check mission inputs, and retry.';for(const b of document.querySelectorAll('[data-review-download]'))b.disabled=true}
 finally{reviewBusy=false;el('reviewCompute').disabled=false;el('reviewCompute').textContent='↗ COMPUTE MISSION DECISION'}}
function reviewScopeFields(){el('reviewRulePower').hidden=el('reviewFocus').value==='geometry';el('reviewRuleGeo').hidden=el('reviewFocus').value==='electrical'}
el('reviewFocus').addEventListener('change',reviewScopeFields);
for(const [reviewId,coId] of [['reviewMinSoc','coMinSoc'],['reviewMinEarth','coMinEarth'],['reviewMaxGap','coMaxGap']]){
 el(reviewId).value=el(coId).value;
 el(reviewId).addEventListener('change',()=>{el(coId).value=el(reviewId).value;markReviewStale()});
 el(coId).addEventListener('change',()=>{el(reviewId).value=el(coId).value;markReviewStale()})}
reviewScopeFields();
el('reviewForm').addEventListener('submit',computeDecisionReview);
el('coJumpReview').addEventListener('click',()=>{location.hash='#/review'});
for(const control of document.querySelectorAll('#reviewForm input,#reviewForm select'))control.addEventListener('input',markReviewStale);
for(const id of ['area','load','battery','orientation','landing','shift','coMinSoc','coMinEarth','coMaxGap','qSite','qStart','qDelay','powerArea','powerLoad','powerBattery','powerMode']){
 const item=el(id);if(item){item.addEventListener('input',markReviewStale);item.addEventListener('change',markReviewStale)}}
for(const id of ['site-connecting_ridge','site-shackleton_rim'])el(id).addEventListener('click',markReviewStale);
for(const b of document.querySelectorAll('[data-review-download]'))b.addEventListener('click',async()=>{
 if(!latestReview)return;const [kind,fmt]=b.dataset.reviewDownload.split('.');b.disabled=true;
 el('reviewDownloadStatus').textContent='Recomputing '+kind+' and generating '+fmt.toUpperCase()+'…';
 try{const r=await fetch('/api/mission-decision/'+kind+'.'+fmt,{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify(reviewPayload()),signal:AbortSignal.timeout(30000)});
 if(!r.ok){const d=await r.json();throw Error(d.detail||'Report generation failed')}
 const blob=await r.blob();const href=URL.createObjectURL(blob);const a=document.createElement('a');a.href=href;
 a.download='POLARIS_'+(r.headers.get('X-POLARIS-REVIEW-ID')||'decision')+'_'+kind+'.'+fmt;
 document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(href),1500);
 el('reviewDownloadStatus').textContent='Generated '+a.download+' from the current mission inputs.'}
 catch(err){el('reviewDownloadStatus').textContent='Export failed: '+err.message}finally{b.disabled=false}});

syncPowerInputs();navigateRoute();

})();
