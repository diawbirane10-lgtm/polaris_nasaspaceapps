"""Mission Decision Brief and adaptive Engineering Simulation Dossier renderers.

Text monochrome. POLARIS emblem and computational charts colored.
XeLaTeX output is generated from each unique mission run; ReportLab provides
portable on-demand PDFs for serverless environments without a TeX installation.
"""
from __future__ import annotations

from io import BytesIO
from math import isfinite
from typing import Any

from .report import _tex_escape, compiled_latex_pdf

COLOR={'original':'#246EA0','delayed':'#C98637','alternative_site_after_delay':'#2A9689'}
NAME={'soc_pct':'Battery state of charge (%)','pv_w':'Photovoltaic output (W)',
      'local_sun_clearance_deg':'Sun over local horizon (degrees)',
      'local_earth_clearance_deg':'Earth over local horizon (degrees)'}

def _esc(v:Any)->str:return _tex_escape(v)

def latex_decision_report(d:dict[str,Any],kind:str)->str:
    if kind not in ('brief','dossier'):raise ValueError('Unknown report variant')
    heading='Mission Decision Brief' if kind=='brief' else 'Engineering Simulation Dossier'
    p=d['inputs'];label=d['mission_label'];sc=d['scenarios']
    selected_rules=[]
    for scenario in sc:
        for c in scenario['checks']:
            selected_rules.append(f"{_esc(scenario['label'])} & {_esc(c['label'])} & {c['observed']:.2f} & {_esc(c['op'])} {c['threshold']:.2f} {_esc(c['unit'])} & {_esc(c['status'])}" + ' ' + '\\'*2)
    rows='\n'.join(f"{_esc(x['label'])} & {_esc(x['site'].split(' / ')[0])} & {_esc(x['decision'])}" + ' ' + '\\'*2 for x in sc)
    eventrows='\n'.join(f"{_esc(s['label'])} & {e['hour']:.1f} h & {_esc(e['description'])}" + ' ' + '\\'*2 for s in sc for e in s['events'])
    diffs='\n'.join(r'\item '+_esc(x['from']+' → '+x['to']+': '+', '.join(f'{k}: {v:+g}' for k,v in x['metric_deltas'].items())) for x in d['comparison'])
    if not diffs:diffs=r'\item No alternative scenario selected for quantitative comparison.'
    ev_section= (r'\section*{Detected events from simulation traces}\begin{longtable}{p{3.0cm}p{1.6cm}p{10cm}}\toprule Scenario & Time & Observed transition\\\midrule\endhead '+eventrows+r'\bottomrule\end{longtable}') if eventrows else (r'\section*{Detected events from simulation traces} No threshold crossings or tracked local-horizon transitions were detected at the sampled epochs.' if p.get('include_events',True) else '')
    plots=[]
    for field in d['chart_fields']:
        vals=[v[field] for s in sc for v in s['trace']]
        if not vals:continue
        low=min(vals);hi=max(vals);span=hi-low
        if span<0.1:low-=1;hi+=1
        else:low-=span*0.12;hi+=span*0.12
        code=[r'\begin{tikzpicture}\begin{axis}[width=\linewidth,height=7cm,xlabel={Elapsed mission time (h)},ylabel={'+_esc(NAME[field])+r'},grid=major,grid style={black!12},legend style={draw=none,at={(.5,-.25)},anchor=north,legend columns=1},ymin='+f'{low:.4f}'+',ymax='+f'{hi:.4f}'+']']
        for s in sc:
            rgb=COLOR[s['key']].lstrip('#');coords=' '.join(f"({v['hours_from_start']:.2f},{v[field]:.4f})" for v in s['trace'])
            if not coords:continue
            code.append(r'\addplot+[no marks,ultra thick,color={rgb,255:red,'+str(int(rgb[0:2],16))+';green,'+str(int(rgb[2:4],16))+';blue,'+str(int(rgb[4:6],16))+'}] coordinates {'+coords+'};')
            code.append(r'\addlegendentry{'+_esc(s['label'])+'}')
        code.append(r'\end{axis}\end{tikzpicture}')
        plots.append(r'\subsection*{'+_esc(NAME[field])+r'}\par '+'\n'.join(code))
    if kind=='brief':
        detail=r''
        event_section=''
    else:
        detail=r'\newpage\section*{Simulation curves}\par '+('\n'.join(plots) if plots else 'Time-series inclusion disabled for this review.')+'\n'+ev_section
        event_section=(r'\section*{Model settings and traceability}\begin{tabularx}{\linewidth}{lX} '
            + r'Dataset SHA-256 & \texttt{' + d['dataset_sha256'] + r'}' + r'\\ '
            + r'Local skyline radius & 6 km' + r'\\ '
            + r'Temporal sampling & 6 hours' + r'\\ '
            + r'Model focus & ' + _esc(d['analysis_scope']) + r'\\ '
            + r'\end{tabularx}' + '\n' + r'\section*{Data resources}\begin{itemize}'
            + '\n'.join(r'\item '+_esc(x['name']+': '+x['url']) for x in d['data_sources'])
            + r'\end{itemize}')
    base=r'''\documentclass[10pt,a4paper]{article}
\usepackage{fontspec}
\setmainfont{LibertinusSerif-Regular.otf}[BoldFont=LibertinusSerif-Bold.otf,ItalicFont=LibertinusSerif-Italic.otf]
\usepackage[margin=19mm,headheight=25pt]{geometry}
\usepackage{booktabs,longtable,tabularx,array,microtype,pgfplots,tikz,xcolor,fancyhdr}
\pgfplotsset{compat=1.18}
\definecolor{polarisblue}{HTML}{246EA0}\definecolor{polariscyan}{HTML}{2A9689}\definecolor{polarisgold}{HTML}{C98637}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{\small POLARIS | Mission Decision Intelligence}\fancyhead[R]{\small REPORTKIND}
\fancyfoot[L]{\scriptsize NASA Space Apps 2026}\fancyfoot[R]{\scriptsize Page \thepage}\renewcommand{\headrulewidth}{.35pt}
\begin{document}
\thispagestyle{empty}
\noindent\begin{minipage}{.19\linewidth}\begin{tikzpicture}[scale=.8]\draw[polarisblue,line width=1.7pt](0,0)circle(1);\draw[polariscyan,line width=1.5pt,rotate=38](0,0)ellipse(1.35 and .38);\fill[polarisgold](.78,.58)circle(.12);\end{tikzpicture}\end{minipage}
\begin{minipage}{.8\linewidth}\fontsize{25}{29}\selectfont\textbf{\textcolor{polarisblue}{POLARIS}}\\\normalsize Mission Decision Intelligence\end{minipage}
\vspace{.65cm}\hrule\vspace{.45cm}
{\LARGE\textbf{REPORTKIND}}\\[.15cm]
{\large MISSIONLABEL}\\[.15cm]
{\small Review ID: REVIEWID | Generated UTC: GENERATED | Data fingerprint: FINGERPRINT}\par
{\small AUTHORLINE}\par
\vspace{.4cm}
\section*{Decision synopsis}
\textbf{MISSIONSTATUS}. REVIEWTEXT
\par\smallskip
\begin{tabularx}{\linewidth}{lX} Mission focus & FOCUS \\ Starting UTC & START \\ Duration / delay & DURATION h / DELAY h \\ Panel area / load / storage & PV m$^2$ / LOAD W / BATTERY kWh \\\end{tabularx}
\section*{Scenario assessment}
\begin{tabularx}{\linewidth}{@{}p{3.2cm}X p{4cm}@{}}\toprule Scenario & Observer & Outcome \\\midrule
SCENARIOROWS
\bottomrule\end{tabularx}
\section*{Engineering criteria actually checked}
\small\begin{longtable}{@{}p{3cm}p{4cm}rp{3cm}l@{}}\toprule Scenario & Criterion & Observed & Required & Result\\\midrule\endhead
CHECKROWS
\bottomrule\end{longtable}\normalsize
\section*{Quantified comparison}
\begin{itemize}DIFFS\end{itemize}
\section*{Decision record}
Engineers select acceptance thresholds and retain responsibility for operational decisions. The recorded numerical comparison uses local topographic geometry and engineering-model energy predictions; uncertainty remains in distant terrain, link budget and spacecraft subsystem fidelity.
DETAILSECTION
EVENTSECTION
\end{document}
'''
    for a,b in {'REPORTKIND':_esc(heading),'MISSIONLABEL':_esc(label),'REVIEWID':d['review_id'],
       'GENERATED':_esc(d['generated_utc']),'FINGERPRINT':d['dataset_sha256'][:16],
       'AUTHORLINE':_esc('Prepared by: '+d.get('prepared_by','Public demonstration (no verified author)') + (' | Audit: '+str(d['audit_id']) if d.get('audit_id') else '')),
       'MISSIONSTATUS':_esc(d['status']),'REVIEWTEXT':_esc(d['interpretation']),
       'FOCUS':_esc(d['focus']),'START':_esc(p['start']),'DURATION':str(p['duration_hours']),
       'DELAY':str(p['delay_hours']),'PV':f"{p['pv_area_m2']:g}",'LOAD':f"{p['load_w']:g}",
       'BATTERY':f"{p['battery_kwh']:g}",'SCENARIOROWS':rows,'CHECKROWS':'\n'.join(selected_rules),
       'DIFFS':diffs,'DETAILSECTION':detail,'EVENTSECTION':event_section}.items():base=base.replace(a,b)
    return base


def portable_decision_pdf(d:dict[str,Any],kind:str)->bytes:
    """Portable print layout for FastAPI/Vercel; no browser-provided metric can enter."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,
                                   PageBreak,KeepTogether,Flowable)
    from xml.sax.saxutils import escape
    import os
    font='/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf'
    bold='/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'
    if os.path.isfile(font):
        pdfmetrics.registerFont(TTFont('PolR',font));pdfmetrics.registerFont(TTFont('PolB',bold));normal,heavy='PolR','PolB'
    else: normal,heavy='Times-Roman','Times-Bold'
    title='Mission Decision Brief' if kind=='brief' else 'Engineering Simulation Dossier'
    buf=BytesIO();width,height=A4;usable=width-86
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=43,rightMargin=43,topMargin=56,bottomMargin=46,
        title=f'POLARIS {title} {d["review_id"]}',author=d.get('prepared_by', 'POLARIS public demonstration'))
    st={n:ParagraphStyle('pol'+n,fontName=(heavy if n in ('title','h','label') else normal),
         fontSize=fs,leading=lead,textColor=colors.black,spaceBefore=sb,spaceAfter=sa)
        for n,fs,lead,sb,sa in [('title',20,25,0,14),('h',12,16,12,7),('body',9.5,13,0,7),
                               ('small',8.3,11,0,5),('label',9,12,0,3)]}
    def para(s,typ='body'):return Paragraph(escape(str(s)),st[typ])
    def tabl(rows,ww):
        t=Table([[para(v,'small') for v in row] for row in rows],colWidths=ww,hAlign='LEFT',repeatRows=1)
        t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),
               ('BOTTOMPADDING',(0,0),(-1,-1),5),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeeee')),
               ('LINEBELOW',(0,0),(-1,0),.5,colors.black),('LINEBELOW',(0,-1),(-1,-1),.3,colors.black)]))
        return t
    def page(cv,doc):
        cv.saveState();cv.setStrokeColor(colors.black);cv.setLineWidth(.35);cv.line(43,height-43,width-43,height-43)
        cv.setFont(heavy,8);cv.drawString(43,height-35,'POLARIS | MISSION ENGINEERING');cv.setFont(normal,8)
        cv.drawRightString(width-43,height-35,title.upper());cv.line(43,36,width-43,36)
        cv.drawString(43,25,'NASA SPACE APPS CHALLENGE 2026');cv.drawRightString(width-43,25,f'{doc.page}');cv.restoreState()
    class Logo(Flowable):
        def __init__(self):super().__init__();self.width=usable;self.height=62
        def draw(self):
            c=self.canv;c.saveState();c.setStrokeColor(colors.HexColor('#246EA0'));c.setLineWidth(1.7);c.circle(26,32,18)
            c.translate(26,32);c.rotate(32);c.setStrokeColor(colors.HexColor('#2A9689'));c.ellipse(-28,-7,28,7)
            c.rotate(-32);c.setFillColor(colors.HexColor('#C98637'));c.circle(13,13,3,fill=1,stroke=0)
            c.translate(-26,-32);c.setFont(heavy,24);c.setFillColor(colors.HexColor('#246EA0'));c.drawString(64,33,'POLARIS')
            c.setFillColor(colors.black);c.setFont(normal,10);c.drawString(66,18,'Mission Decision Intelligence');c.restoreState()
    story=[Logo(),para(title,'title'),para(d['mission_label']),
       para('Review ID: '+d['review_id']+' | Generated: '+d['generated_utc'],'small'),
       para('Prepared by: '+d.get('prepared_by','Public demonstration (no verified author)'), 'small'),
       para('Audit: '+str(d['audit_id']), 'small') if d.get('audit_id') else Spacer(1,0),
       para('Mission scope and selected requirements','h')]
    inp=d['inputs']
    story.append(tabl([['PARAMETER','VALUE'],['Study type',d['focus']],['Start UTC',inp['start']],
        ['Duration and delay',f"{inp['duration_hours']} h / {inp['delay_hours']} h"],
        ['PV / electrical load / battery',f"{inp['pv_area_m2']} m² / {inp['load_w']} W / {inp['battery_kwh']} kWh"],
        ['Dataset SHA-256 prefix',d['dataset_sha256'][:24]]],[190,usable-190]))
    story += [para('Mission decision synopsis','h'),para(d['status'],'label'),para(d['interpretation'],'small')]
    rr=[['SCENARIO','OBSERVATION POINT','ENGINEERING STATUS']]
    for s in d['scenarios']:rr.append([s['label'],s['site'].split(' / ')[0],s['decision']])
    story+=[tabl(rr,[145,155,usable-300]),para('Evaluated criteria','h')]
    cr=[['SCENARIO / RULE','MEASURED','REQUIREMENT','STATE']]
    for sc in d['scenarios']:
        for rule in sc['checks']:
            cr.append([sc['label']+': '+rule['label'],f"{rule['observed']:.2f} {rule['unit']}",
                f"{rule['op']} {rule['threshold']:.2f} {rule['unit']}",rule['status']])
    story.append(tabl(cr,[220,90,118,usable-428]))
    if d['comparison']:
        story.append(para('Quantified changes','h'))
        for diff in d['comparison']:
            story.append(para(diff['from']+' → '+diff['to']+': '+', '.join(f"{k} {v:+.3f}" for k,v in diff['metric_deltas'].items()),'small'))
    if kind=='dossier':
        class Plot(Flowable):
            def __init__(self,field):super().__init__();self.width=usable;self.height=217;self.field=field
            def draw(self):
                c=self.canv;W=self.width;H=self.height;left=50;right=18;top=22;bottom=38
                values=[r[self.field] for s in d['scenarios'] for r in s['trace']]
                if not values:return
                vmin,vmax=min(values),max(values);pad=(vmax-vmin)*.12 if vmax>vmin else 1
                vmin-=pad;vmax+=pad;dx=W-left-right;dy=H-top-bottom
                maximum=max(r['hours_from_start'] for s in d['scenarios'] for r in s['trace']) or 1
                c.setFont(normal,8)
                for i in range(5):
                    val=vmin+(vmax-vmin)*i/4;y=bottom+i*dy/4
                    c.setStrokeColor(colors.HexColor('#dedede'));c.setLineWidth(.4);c.line(left,y,W-right,y)
                    c.setFillColor(colors.black);c.drawRightString(left-5,y-3,f'{val:.1f}')
                c.drawCentredString(left+dx/2,11,'Elapsed mission time (hours)')
                for sc in d['scenarios']:
                    series=sc['trace'];c.setLineWidth(2);c.setStrokeColor(colors.HexColor(COLOR[sc['key']]))
                    pa=c.beginPath()
                    for i,v in enumerate(series):
                        x=left+dx*v['hours_from_start']/maximum;y=bottom+dy*(v[self.field]-vmin)/(vmax-vmin)
                        (pa.moveTo if i==0 else pa.lineTo)(x,y)
                    c.drawPath(pa)
        story.append(PageBreak());story.append(para('Simulation traces','h'))
        for field in d['chart_fields']:
            if d['scenarios'][0]['trace']:
                story.extend([para(NAME[field],'label'),Plot(field),Spacer(1,9)])
                for sc in d['scenarios']:
                    story.append(para(sc['label']+' — '+sc['site'].split(' / ')[0],'small'))
        if d['inputs']['include_events']:
            story.append(para('Events derived from actual samples','h'))
            anyev=False
            for sc in d['scenarios']:
                for ev in sc['events']:
                    story.append(para(sc['label']+f" / {ev['hour']} h: "+ev['description'],'small'));anyev=True
            if not anyev:story.append(para('No tracked threshold or skyline crossings were detected in the sampled windows.','small'))
        story.append(para('Calculation settings and dataset provenance','h'))
        for key,value in d['model_settings'].items():story.append(para(f'{key}: {value}','small'))
        for src in d['data_sources']:story.append(para(src['name']+': '+src['role']+' | '+src['url'],'small'))
        story.append(para('Dataset SHA-256: '+d['dataset_sha256'],'small'))
    else:
        story.append(para('Review and follow-up','h'))
        story.append(para('Review the flagged criteria and rerun a modified mission. Full curves, event records, and model evidence are available in the Engineering Simulation Dossier.','small'))
    doc.build(story,onFirstPage=page,onLaterPages=page)
    pdf=buf.getvalue()
    if not pdf.startswith(b'%PDF'):raise RuntimeError('Unable to render Mission Decision Report')
    return pdf


def make_decision_pdf(d:dict[str,Any],kind:str,prefer_latex:bool=False)->tuple[bytes,str]:
    source=latex_decision_report(d,kind)
    if prefer_latex:
        pdf=compiled_latex_pdf(source)
        if pdf:return pdf,'xelatex / Libertinus Serif'
    return portable_decision_pdf(d,kind),'ReportLab (serif fallback on Vercel)'
