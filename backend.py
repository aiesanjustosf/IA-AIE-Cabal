
import re, datetime, pdfplumber, pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def _to_float(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))

def extract_summary(pdf_bytes: bytes):
    tmp = "_input.pdf"
    with open(tmp, "wb") as f:
        f.write(pdf_bytes)

    rx_iva21 = re.compile(r"IVA\s*S/ARANCEL\s*DE\s*DESCUENTO\s+21,00%[^\n\r]*?(\d{1,3}(?:\.\d{3})*,\d{2})\s*[-−]", re.IGNORECASE)
    rx_iva105 = re.compile(r"IVA\s*S/COSTO\s*FINANCIERO\s+10,50%[^\n\r]*?(\d{1,3}(?:\.\d{3})*,\d{2})\s*[-−]", re.IGNORECASE)
    rx_perc = re.compile(r"PERCEPCION\s*DE\s*IVA\s*RG\s*333[^\n\r]*?(\d{1,3}(?:\.\d{3})*,\d{2})\s*[-−]", re.IGNORECASE)
    rx_ret = re.compile(r"RETENCION\s*DE\s*INGRESOS\s*BR[^\n\r]*?(\d{1,3}(?:\.\d{3})*,\d{2})\s*[-−]", re.IGNORECASE)
    rx_menos_iva = re.compile(r"[-−]\s*IVA(?:\s*21,00%)?[^\n\r]*?(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE)

    iva21 = iva105 = perc = ret = 0.0

    with pdfplumber.open(tmp) as pdf:
        for page in pdf.pages:
            text = (page.extract_text() or "").replace("−", "-")
            for m in rx_iva21.finditer(text):
                iva21 += _to_float(m.group(1))
            for m in rx_iva105.finditer(text):
                iva105 += _to_float(m.group(1))
            for m in rx_perc.finditer(text):
                perc += _to_float(m.group(1))
            for m in rx_ret.finditer(text):
                ret += _to_float(m.group(1))
            for m in rx_menos_iva.finditer(text):
                iva21 += _to_float(m.group(1))

    base21 = round(iva21/0.21, 2) if iva21 else 0.0
    base105 = round(iva105/0.105, 2) if iva105 else 0.0

    resumen = pd.DataFrame({
        "Concepto": [
            "Base Neto Arancel (21%)",
            "IVA 21% sobre Arancel (incluye -IVA)",
            "Base Neto Costo Financiero (10,5%)",
            "IVA 10,5% sobre Costo Financiero",
            "Percepciones IVA RG 333",
            "Retenciones de Ingresos Brutos",
        ],
        "Monto": [
            round(base21, 2),
            round(iva21, 2),
            round(base105, 2),
            round(iva105, 2),
            round(perc, 2),
            round(ret, 2),
        ]
    })
    return resumen

def money(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def build_pdf(resumen_df: pd.DataFrame, out_path: str, titulo: str):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(out_path, pagesize=A4)
    story = []
    story.append(Paragraph(titulo, styles["Title"]))
    story.append(Paragraph(f"Generado: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Resumen de importes", styles["Heading2"]))
    data = [["Concepto", "Monto ($)"]] + [[c, money(v)] for c, v in resumen_df.values]
    tbl = Table(data, colWidths=[360, 140])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#222")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#f7f7f7"), colors.white]),
    ]))
    story.append(tbl)
    doc.build(story)
    return out_path
