import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {title:"POLARIS / Mission Control V2 — Experimental",description:"Independent experimental Mission Control interface, grounded in POLARIS lunar engineering data."};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}