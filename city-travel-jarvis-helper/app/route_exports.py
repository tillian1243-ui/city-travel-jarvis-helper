import html,io

def points(route):return sorted(route.get("points",[]),key=lambda x:int(x.get("sequence",0)))
def build_gpx(route):
    title=html.escape(str(route.get("title","City Jarvis route")));rows=['<?xml version="1.0" encoding="UTF-8"?>','<gpx version="1.1" creator="City & Travel Jarvis" xmlns="http://www.topografix.com/GPX/1/1">',f'<metadata><name>{title}</name></metadata>',f'<trk><name>{title}</name><trkseg>']
    for p in points(route):rows.append(f'<trkpt lat="{float(p["latitude"]):.7f}" lon="{float(p["longitude"]):.7f}"><name>{html.escape(str(p.get("name","")))}</name></trkpt>')
    rows+=['</trkseg></trk>','</gpx>'];return '\n'.join(rows).encode()
def build_kml(route):
    title=html.escape(str(route.get("title","City Jarvis route")));coords=' '.join(f'{float(p["longitude"]):.7f},{float(p["latitude"]):.7f},0' for p in points(route));return f'<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>{title}</name><Placemark><LineString><coordinates>{coords}</coordinates></LineString></Placemark></Document></kml>'.encode()
def build_pdf(payload):
    from pathlib import Path
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    regular = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    bold = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    font_regular, font_bold = "Helvetica", "Helvetica-Bold"
    if regular.exists() and bold.exists():
        if "CityDejaVu" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("CityDejaVu", str(regular)))
            pdfmetrics.registerFont(TTFont("CityDejaVu-Bold", str(bold)))
        font_regular, font_bold = "CityDejaVu", "CityDejaVu-Bold"

    b=io.BytesIO();c=canvas.Canvas(b,pagesize=A4);w,h=A4;y=h-50
    c.setTitle(str(payload.get("title","City & Travel Jarvis guide"))[:120])
    c.setFont(font_bold,18);c.drawString(48,y,str(payload.get("title","City & Travel Jarvis guide"))[:80]);y-=30
    c.setFont(font_regular,10)
    for sec in payload.get("sections",[]):
        c.setFont(font_bold,13);c.drawString(48,y,str(sec.get("title","Раздел"))[:90]);y-=20;c.setFont(font_regular,10)
        for item in sec.get("items",[]):
            text=f'{item.get("time") or item.get("label") or "•"} — {item.get("text") or item.get("title") or ""}'
            for chunk in [text[i:i+95] for i in range(0,len(text),95)]:c.drawString(48,y,chunk);y-=14
            if y<60:c.showPage();y=h-50;c.setFont(font_regular,10)
        y-=8
    c.save();return b.getvalue()
