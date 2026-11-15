import {NextRequest,NextResponse} from "next/server";
const BASE="https://polaris-spaceapps-2026.vercel.app";
export async function GET(req:NextRequest){
  const site=req.nextUrl.searchParams.get("site")||"connecting_ridge";
  if(!["connecting_ridge","shackleton_rim"].includes(site))return NextResponse.json({error:"Invalid reference site"},{status:400});
  try{
    const res=await fetch(BASE+"/api/nasa-reference/"+site,{next:{revalidate:60},signal:AbortSignal.timeout(12000)});
    if(!res.ok)return NextResponse.json({error:"Reference service unavailable",upstream:res.status},{status:502});
    return NextResponse.json(await res.json(),{headers:{"Cache-Control":"public, max-age=60"}});
  }catch{return NextResponse.json({error:"NASA reference API unavailable; no synthetic data shown"},{status:503});}
}