import {NextRequest,NextResponse} from "next/server";
const BASE="https://polaris-spaceapps-2026.vercel.app";
export async function POST(req:NextRequest){
 const raw=await req.text();
 if(raw.length>12000)return NextResponse.json({detail:"Payload too large"},{status:413});
 try{
  const x=JSON.parse(raw);
  if(typeof x.question!=="string"||x.question.length>2000)return NextResponse.json({detail:"Invalid question"},{status:422});
  const res=await fetch(BASE+"/api/copilot",{method:"POST",headers:{"Content-Type":"application/json"},body:raw,cache:"no-store",signal:AbortSignal.timeout(35000)});
  return NextResponse.json(await res.json(),{status:res.status,headers:{"Cache-Control":"no-store"}});
 }catch{return NextResponse.json({detail:"Engineering Copilot service unavailable"},{status:503})}
}