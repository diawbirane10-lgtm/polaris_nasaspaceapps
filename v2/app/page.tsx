"use client";
import {useEffect,useMemo,useState} from "react";
import {Activity,ArrowDownRight,ArrowRight,ArrowUpRight,Atom,BatteryCharging,BookOpen,CheckCircle2,ChevronDown,Command,Compass,Database,Download,ExternalLink,Eye,FileCheck2,Globe2,Layers3,Menu,MessageSquareText,Moon,Orbit,PanelLeftClose,Play,Radio,Radar,RefreshCw,Satellite,ShieldCheck,SlidersHorizontal,Sun,Terminal,TriangleAlert,Wifi, X, Zap} from "lucide-react";

type Sample={utc:string;sun_az:number;sun_el:number;earth_az:number;earth_el:number;sun_margin_deg:number;earth_margin_deg:number;sun_visible:boolean;earth_visible:boolean;pv_w:number;soc:number;sample_hours:number};
type Reference={site_key:string;site:{name:string;lat_deg:number;lon_e_deg:number;height_km:number};source:string;source_type:string;samples:Sample[];summary:{sun_visible_hours:number;earth_visible_hours:number;max_earth_gap_hours:number;min_soc_pct:number;unserved_energy_kwh:number;duration_hours:number;sun_visible_pct:number;earth_visible_pct:number};assumptions:{load_w:number;pv_area_m2:number;battery_kwh:number;initial_soc_pct:number;pv_efficiency:number};limitations:string[];data_provenance:{dem_sha256:string;sample_interval_hours:number;range_km:number;dem_url:string;jpl_api:string}};
type Tab="mission"|"terrain"|"scenarios"|"power"|"atlas"|"evidence"|"copilot"|"review";
const tabs:{id:Tab;name:string;sub:string;icon:any}[]=[
 {id:"mission",name:"Mission",sub:"Overview",icon:Orbit},
 {id:"terrain",name:"Sky & Terrain",sub:"Solar geometry",icon:Radar},
 {id:"scenarios",name:"Scenarios",sub:"Mission timeline",icon:Layers3},
 {id:"power",name:"Power Systems",sub:"Energy budget",icon:Zap},
 {id:"atlas",name:"Lunar Atlas",sub:"Site exploration",icon:Moon},
 {id:"evidence",name:"Evidence",sub:"Scientific provenance",icon:Database},
 {id:"copilot",name:"AI Copilot",sub:"Groq + Python",icon:MessageSquareText},
 {id:"review",name:"Decision Review",sub:"Requirements",icon:FileCheck2}
];
const headings:Record<Tab,[string,string,string]>={
 mission:["MISSION DIRECTOR","Lunar mission intelligence","Select a NASA reference site, inspect calculated geometry and assess mission conditions."],
 terrain:["GEOMETRY SYSTEM","Sky & terrain visibility","Solar and Earth observer geometry calculated with NASA reference inputs."],
 scenarios:["TEMPORAL ANALYSIS","Mission scenarios","Review sampled mission time against solar visibility and electrical state."],
 power:["ENERGY SYSTEMS","DC power & survival envelope","Solar input, battery energy balance, and continuous mission electrical demand."],
 atlas:["GEOSPATIAL INTELLIGENCE","Lunar reference sites","Reference coordinates and schematic landscape context for two south-pole locations."],
 evidence:["TRACEABILITY SYSTEM","Scientific evidence","Dataset provenance, sampling assumptions and explicit model limitations."],
 copilot:["MISSION INTELLIGENCE","Engineering AI Copilot","Ask a technical question. Natural-language explanations use the real Python mission service."],
 review:["DECISION GOVERNANCE","Mission decision review","Compare the current computed results with transparent, editable engineering thresholds."]
};
const APP="https://polaris-spaceapps-2026.vercel.app";
const fmt=(n:number,d=1)=>Number.isFinite(n)?n.toFixed(d):"—";
const clock=(u:string)=>u?new Date(u).toLocaleString("en-GB",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"UTC",hour12:false}):"—";
function Trend({values,color="#36c6db",height=72}:{values:number[];color?:string;height?:number}){
 const min=Math.min(...values,0),max=Math.max(...values,1);const range=max-min||1;
 const points=values.map((v,i)=>`${12+(i/Math.max(1,values.length-1))*576},${height-12-((v-min)/range)*(height-24)}`).join(" ");
 return <svg aria-hidden="true" className="mini-chart" viewBox={`0 0 600 ${height}`} preserveAspectRatio="none"><path d={`M 12 ${height-12} H 588`} stroke="#394758" strokeWidth="1" strokeDasharray="3 6" fill="none"/><polyline points={points} fill="none" stroke={color} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
function LunarScene({refData,sample,site}:{refData:Reference|null;sample:Sample|null;site:string}){
 return <div className="world-scene" role="img" aria-label="Stylized lunar terrain diagram, not a geometrically accurate NASA terrain mesh">
  <div className="scene-noise"/><div className="scene-star s1"/><div className="scene-star s2"/><div className="scene-star s3"/>
  <div className="scene-crater c1"/><div className="scene-crater c2"/><div className="scene-crater c3"/><div className="scene-crater c4"/><div className="scene-crater c5"/>
  <div className="scene-orbit o1"/><div className="scene-orbit o2"/>
  <div className="scene-crosshair"><span/><b>01</b></div>
  <div className="scene-trace t1"/><div className="scene-trace t2"/>
  <div className="scene-flag"><span className="pulse-dot"/><strong>{site==="connecting_ridge"?"CONNECTING RIDGE":"SHACKLETON RIM"}</strong><small>SELECTED SITE · REFERENCE LOCATION</small></div>
  <div className="scene-coords"><span>LATITUDE {refData?fmt(refData.site.lat_deg,4)+"°":"—"}</span><span>LONGITUDE {refData?fmt(refData.site.lon_e_deg,4)+"° E":"—"}</span><span>HEIGHT {refData?fmt(refData.site.height_km,3)+" km":"—"}</span></div>
  <div className="scene-compass">N <span>＋</span> 090°</div>
  <div className="scene-bottom"><span>SCHEMATIC TERRAIN VISUALIZATION</span><span>NOT A GEOREGISTERED DEM RENDER</span></div>
  {sample&&<div className="scene-telemetry"><div><Sun size={14}/> SOLAR ELEVATION <b>{fmt(sample.sun_el,2)}°</b></div><div><Globe2 size={14}/> EARTH ELEVATION <b>{fmt(sample.earth_el,2)}°</b></div></div>}
 </div>
}
export default function Page(){
 const [active,setActive]=useState<Tab>("mission"),[site,setSite]=useState("connecting_ridge"),[data,setData]=useState<Reference|null>(null),[error,setError]=useState(""),[loading,setLoading]=useState(true),[tick,setTick]=useState(0),[mode,setMode]=useState<"dark"|"light">("dark"),[menu,setMenu]=useState(false);
 const [question,setQuestion]=useState("Explain the energy balance for 400 W of constant electrical demand."),[answer,setAnswer]=useState(""),[askBusy,setAskBusy]=useState(false),[copilotMode,setCopilotMode]=useState("");
 const [reserve,setReserve]=useState(20),[minEarth,setMinEarth]=useState(6);
 useEffect(()=>{let live=true;setLoading(true);setData(null);setError("");setTick(0);fetch("/api/reference?site="+site).then(async r=>{if(!r.ok)throw Error("Reference endpoint returned "+r.status);return r.json()}).then(j=>{if(live)setData(j)}).catch(e=>{if(live)setError(e.message)}).finally(()=>{if(live)setLoading(false)});return()=>{live=false}},[site]);
 const sample=data?.samples[Math.min(tick,(data.samples.length-1))]||null;
 const passSoc=data?data.summary.min_soc_pct>=reserve:false;
 const passEarth=data?data.summary.earth_visible_hours>=minEarth:false;
 const resultOk=!!data&&passSoc&&passEarth;
 const values=data?.samples||[];
 const title=headings[active];
 async function ask(){
  if(!question.trim()||askBusy)return;
  setAskBusy(true);setAnswer("");setCopilotMode("RUNNING");
  try{const payload={question,site,start:"2026-11-14T00:00Z",duration_hours:24,delay_hours:48,pv_area_m2:16,load_w:400,battery_kwh:20,panel_mode:"horizontal",action:"explain",min_soc_pct:reserve,min_local_earth_hours:minEarth,max_local_earth_gap_hours:24};
   const r=await fetch("/api/copilot",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
   const j=await r.json();if(!r.ok)throw Error(j.detail||"API failed");
   setAnswer(j.answer||"No response");setCopilotMode(j.mode==="llm_explainer"?"GROQ / PYTHON ENGINE":j.mode==="engineering_fallback"?"PYTHON FALLBACK · "+(j.llm_status||"ERROR"):"ENGINEERING ENGINE");
  }catch(e){setAnswer(e instanceof Error?e.message:"Unable to reach the mission service");setCopilotMode("UNAVAILABLE")}
  finally{setAskBusy(false)}
 }
 return <div className={`app-shell ${mode==="light"?"theme-light":""}`}>
  <div className="app-bar"><div className="brand"><div className="brand-star">✦</div><div><strong>POLARIS<span className="brand-slash"> / </span>CONTROL</strong><small>LUNAR MISSION INTELLIGENCE <span>・</span> V2 EXPERIMENT</small></div></div>
   <div className="app-center"><span className="green-dot"/> REFERENCE DATA {loading?"LOADING":error?"UNAVAILABLE":"SYNCHRONIZED"} <span className="bar-sep">/</span> <span>NASA SPACE APPS 2026</span></div>
   <div className="app-actions"><button aria-label="Toggle contrast theme" className="icon-button" onClick={()=>setMode(mode==="dark"?"light":"dark")}><Sun size={17}/></button><a className="production-link" href={APP+"/demo"} target="_blank" rel="noreferrer">OPEN ORIGINAL <ExternalLink size={13}/></a><button className="mobile-menu" aria-label="Open navigation" onClick={()=>setMenu(!menu)}>{menu?<X/>:<Menu/>}</button></div>
  </div>
  <div className="workbench">
   <aside className={`left-rail ${menu?"menu-open":""}`}>
    <div className="rail-header"><small>SYSTEM MODULES</small><span>08 / 08</span></div>
    <nav aria-label="Mission modules" className="module-nav">{tabs.map((tab,i)=>{const Icon=tab.icon;return <button key={tab.id} className={`module-item ${active===tab.id?"active":""}`} onClick={()=>{setActive(tab.id);setMenu(false)}} aria-current={active===tab.id?"page":undefined}><span className="module-icon"><Icon size={17}/></span><span className="module-copy"><strong>{tab.name}</strong><small>{tab.sub}</small></span><span className="module-num">{String(i+1).padStart(2,"0")}</span></button>})}</nav>
    <div className="rail-bottom"><span>DESIGN INFLUENCE</span><strong>JAPANESE DESIGN SYSTEMS</strong><small>PRECISION · HIERARCHY · LEGIBILITY</small><a href="https://design.digital.go.jp/dads/" target="_blank" rel="noreferrer">DESIGN SOURCE <ArrowUpRight size={12}/></a></div>
   </aside>
   <main className="main-area">
    <div className="context-row"><span>MISSION CONTROL</span><ArrowRight size={12}/><span>{title[0]}</span><span className="context-right">EXPERIMENTAL BUILD / NOT FLIGHT-QUALIFIED</span></div>
    <header className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> {title[0]} <span className="jp">観測 / ANALYSIS</span></div><h1>{title[1]}</h1><p>{title[2]}</p></div><span className="build-label">MC / 02.06 <span>DESIGN TEST</span></span></header>
    <div className="kpi-strip">
     <div className="kpi"><span>MISSION SITE</span><strong className="small-kpi">{site==="connecting_ridge"?"CONNECTING RIDGE":"SHACKLETON RIM"}</strong><small>NASA GSFC LOLA REFERENCE</small></div>
     <div className="kpi"><span>MIN. BATTERY SOC</span><strong>{data?fmt(data.summary.min_soc_pct,1)+"%":"—"}</strong><small>{data?"96h baseline sample":"Waiting for reference"}</small></div>
     <div className="kpi"><span>EARTH VISIBILITY</span><strong>{data?fmt(data.summary.earth_visible_hours,1)+" h":"—"}</strong><small>GEOMETRIC LOCAL HORIZON</small></div>
     <div className="kpi"><span>UNSERVED ENERGY</span><strong>{data?fmt(data.summary.unserved_energy_kwh,2)+" kWh":"—"}</strong><small>MODELLED ELECTRICAL DEFICIT</small></div>
    </div>
    <section className="work-section">
     <div className="section-bar"><div><span className="tiny-index">01 / LIVE WORKSPACE</span><h2>{active==="power"?"Power-system telemetry":active==="copilot"?"Mission intelligence desk":active==="evidence"?"Reference evidence register":active==="review"?"Decision acceptance desk":active==="scenarios"?"Scenario time series":active==="terrain"?"Sun, Earth & local horizon":active==="atlas"?"Lunar geographic context":"Lunar surface observation"}</h2></div><span className="scope-badge"><span className="green-dot"/> {error?"SOURCE OFFLINE":"NASA-SOURCED REFERENCE"}</span></div>
     {error&&<div role="alert" className="api-error"><TriangleAlert size={17}/> {error}. Simulation values are intentionally unavailable; no fabricated fallback.</div>}
     {loading&&<div role="status" className="loading"><RefreshCw size={18} className="spinning"/> Retrieving verified reference samples…</div>}
     {(active==="mission"||active==="terrain"||active==="atlas")&&<LunarScene refData={data} sample={sample} site={site}/>}
     {active==="scenarios"&&<div className="chart-hero"><div className="chart-top"><div><small>SIMULATED BATTERY ENVELOPE</small><h3>Energy autonomy / sampled timeline</h3></div><span>6-HOUR SAMPLING</span></div><Trend values={values.map(v=>v.soc*100)} color="#47d6ce" height={220}/><div className="chart-labels"><span>{values.length?clock(values[0].utc):"—"}</span><span>{values.length?clock(values[values.length-1].utc):"—"}</span></div><p className="subnote">Sample values from the production Python model. Time-series rendering is illustrative between discrete samples.</p></div>}
     {active==="power"&&<div className="power-grid"><div className="power-card"><div className="power-card-head"><small>01 / SOLAR ARRAY</small><Sun size={20}/></div><strong>{sample?fmt(sample.pv_w,1)+" W":"—"}</strong><span>MODELED PV OUTPUT · SELECTED SAMPLE</span><Trend values={values.map(x=>x.pv_w)} height={90} color="#d8aa6c"/></div><div className="power-card"><div className="power-card-head"><small>02 / BATTERY STORAGE</small><BatteryCharging size={20}/></div><strong>{sample?fmt(sample.soc*100,1)+"%":"—"}</strong><span>STATE OF CHARGE · SELECTED SAMPLE</span><Trend values={values.map(x=>x.soc*100)} height={90} color="#53d7c7"/></div><div className="power-flow"><span>PRELIMINARY CONCEPTUAL ARCHITECTURE — NOT ELECTRICALLY SIZED</span><div className="flow-nodes"><b>SOLAR ARRAY</b><ArrowRight/><b>DC/DC</b><ArrowRight/><b>DC BUS</b><ArrowRight/><b>MISSION LOAD</b></div><small>Battery storage is coupled to the simulated DC energy balance. Protection, thermal losses and converter sizing require further engineering.</small></div></div>}
     {active==="evidence"&&<div className="evidence-grid"><div className="evidence-card"><Database size={25}/><small>TOPOGRAPHY</small><strong>NASA GSFC / LOLA</strong><span>{data?.data_provenance?.dem_sha256?.slice(0,16)||"—"}…</span><a href={data?.data_provenance?.dem_url||"https://pgda.gsfc.nasa.gov/"} target="_blank" rel="noreferrer">SOURCE DEM <ExternalLink size={12}/></a></div><div className="evidence-card"><Orbit size={25}/><small>EPHEMERIDES</small><strong>JPL HORIZONS</strong><span>Six-hour observer-geometry samples</span><a href="https://ssd.jpl.nasa.gov/horizons/" target="_blank" rel="noreferrer">SOURCE REFERENCE <ExternalLink size={12}/></a></div><div className="evidence-card"><ShieldCheck size={25}/><small>VALIDITY</small><strong>EXPLICIT LIMITATIONS</strong><span>Local 6 km horizon / preliminary design only</span><a href={APP+"/demo#/evidence"} target="_blank" rel="noreferrer">FULL EVIDENCE <ExternalLink size={12}/></a></div></div>}
     {active==="copilot"&&<div className="chat-work"><div className="chat-intro"><MessageSquareText size={22}/><strong>POLARIS / FLIGHT DIRECTOR</strong><small>Groq language explanations + Python-computed mission evidence</small></div><div className="chat-answer" aria-live="polite">{answer||"Ask about lunar site visibility, PV energy, battery state of charge, or scenario constraints. The engineering engine stays the numerical authority."}</div>{copilotMode&&<span className="answer-mode">{copilotMode}</span>}<label htmlFor="ask">MISSION QUESTION</label><textarea id="ask" value={question} onChange={e=>setQuestion(e.target.value)} maxLength={1800} rows={3}/><button className="send-button" disabled={askBusy||!question.trim()} onClick={ask}>{askBusy?"ANALYZING…":"ASK POLARIS"} <ArrowRight size={16}/></button><small className="subnote">Requests are processed by the original POLARIS API and its third-party LLM provider. Do not enter private data.</small></div>}
     {active==="review"&&<div className="review-layout"><div className="review-form"><small>ENGINEER-DEFINED REQUIREMENTS</small><label htmlFor="reserve">MINIMUM BATTERY SOC <strong>{reserve}%</strong></label><input id="reserve" type="range" min={0} max={100} value={reserve} onChange={e=>setReserve(Number(e.target.value))}/><label htmlFor="earth">MINIMUM LOCAL EARTH VISIBILITY <strong>{minEarth} h</strong></label><input id="earth" type="range" min={0} max={48} value={minEarth} onChange={e=>setMinEarth(Number(e.target.value))}/><p>These are user-defined review limits, not external safety standards.</p></div><div className="review-results"><small>REFERENCE SCENARIO / RULE CHECK</small><div className="review-result">{data?(resultOk?"SELECTED LIMITS PASS":"ONE OR MORE LIMITS FAIL"):"NO SOURCE DATA"}<span className={resultOk?"good":"bad"}>{data?(resultOk?"PASS":"FAIL"):"—"}</span></div><div className="review-rule">BATTERY RESERVE <span>{data?(passSoc?"PASS":"FAIL"):"—"}</span></div><div className="review-rule">EARTH VISIBILITY <span>{data?(passEarth?"PASS":"FAIL"):"—"}</span></div><a href={APP+"/demo#/decision-review"} target="_blank" rel="noreferrer">OPEN FULL ENGINEERING DECISION REVIEW <ArrowUpRight size={14}/></a></div></div>}
     <div className="timeline-panel"><div className="timeline-head"><div><small>TIME NAVIGATION / NASA REFERENCE</small><strong>{sample?clock(sample.utc)+" UTC":"Awaiting data"}</strong></div><span>{values.length?String(tick+1).padStart(2,"0")+" / "+String(values.length).padStart(2,"0"):"-- / --"} SAMPLES</span></div><input aria-label="Select reference time sample" className="timeline-slider" type="range" min={0} max={Math.max(0,values.length-1)} step={1} value={tick} disabled={!values.length} onChange={e=>setTick(Number(e.target.value))}/><div className="timeline-edges"><span>{values.length?clock(values[0].utc):"—"}</span><span>6 H INTERVAL</span><span>{values.length?clock(values.at(-1)!.utc):"—"}</span></div></div>
    </section>
    <footer className="work-footer"><span>POLARIS // JAPANESE-INSPIRED INTERFACE EXPERIMENT</span><span>REFERENCE DATA: PRODUCTION NASA / PYTHON ENGINE</span><span>© 2026 POLARIS</span></footer>
   </main>
   <aside className="right-rail"><div className="right-top"><div><span>MISSION CONFIGURATION</span><h2>Active observation</h2></div><SlidersHorizontal size={18}/></div><div className="side-section"><label htmlFor="site">SELECT REFERENCE SITE</label><div className="custom-select"><select id="site" value={site} onChange={e=>setSite(e.target.value)}><option value="connecting_ridge">Connecting Ridge / Site01</option><option value="shackleton_rim">Shackleton Rim / Site04</option></select><ChevronDown size={15}/></div><p>Two NASA LOLA reference sample locations. Neither is a certified landing zone.</p></div>
    <div className="side-section metric-section"><div className="side-title">LOCAL GEOMETRY <span>LIVE SAMPLE</span></div>
     <div className="geometry-metric"><span><Sun size={15}/> SUN ELEVATION</span><strong>{sample?fmt(sample.sun_el,2)+"°":"—"}</strong></div>
     <div className="geometry-metric"><span><Globe2 size={15}/> EARTH ELEVATION</span><strong>{sample?fmt(sample.earth_el,2)+"°":"—"}</strong></div>
     <div className="geometry-metric"><span><Compass size={15}/> SUN MARGIN</span><strong>{sample?fmt(sample.sun_margin_deg,2)+"°":"—"}</strong></div>
     <div className="geometry-metric"><span><Radio size={15}/> EARTH CLEARANCE</span><strong className={sample?.earth_visible?"text-good":"text-alert"}>{sample?(sample.earth_visible?"VISIBLE":"OBSTRUCTED"):"—"}</strong></div></div>
    <div className="side-section"><div className="side-title">ELECTRICAL BUS <span>MODEL OUTPUT</span></div><div className="bus-card"><div><span>PV SUPPLY</span><b>{sample?fmt(sample.pv_w,1)+" W":"—"}</b></div><div className="bus-bar"><span style={{width:sample?Math.min(100,Math.max(0,(sample.pv_w/(data?.assumptions.load_w||400))*100))+"%":"0%"}}/></div><div><span>CONTINUOUS LOAD</span><b>{data?fmt(data.assumptions.load_w,0)+" W":"—"}</b></div><div className="bus-bar"><span style={{width:"100%",background:"#c49562"}}/></div></div><small className="side-note">Modeled supply and load are not power-electronics circuit validation.</small></div>
    <div className="side-section side-provenance"><ShieldCheck size={19}/><div><strong>EVIDENCE-LINKED SYSTEM</strong><p>NASA/JPL reference data, six-hour cadence and a simplified energy model. All limitations remain applicable.</p></div></div>
    <a className="full-app-link" href={APP+"/demo"} target="_blank" rel="noreferrer">OPEN CERTIFIED WORKFLOW? <ExternalLink size={14}/><small>Original research prototype / not flight-certified</small></a>
   </aside>
  </div><div className="test-watermark">V2 UI EXPERIMENT — NOT THE NASA SUBMISSION</div>
 </div>
}
