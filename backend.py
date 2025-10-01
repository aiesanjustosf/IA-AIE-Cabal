
import re, datetime, pdfplumber, pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def _to_float(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))

def _fmt(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def extract_summary(pdf_bytes: bytes) -> pd.DataFrame:
    """
    Reads the whole PDF and returns a 6-row summary:
      1. Base Neto Arancel 21%
      2. IVA 21% sobre Arancel (incluye -IVA en Debitos al Comercio)
      3. Base Neto Costo Financiero 10,5%
      4. IVA 10,5% sobre Costo Financiero
      5. Percepciones IVA RG 333
      6. Retenciones de Ingresos Brutos
    Note: The '-IVA 21%' line is not shown separately.
    """
    tmp = "_aie_input.pdf"
    with open(tmp, "wb") as f:
        f.write(pdf_bytes)

    rx_iva21_arancel = re.compile(r"IVA\s*S/ARANCEL\s*DE\s*DESCUENTO\s*21,00%[^0-9]*(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE)
    rx_minus_iva21  = re.compile(r"[−-]\s*IVA\s*21,00%[^0-9]*(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE)
    rx_iva105_costo = re.compile(r"IVA\s*S/COSTO\s*FINANCIERO\s*10,50%[^0-9]*(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE)
    rx_perc_rg333   = re.compile(r"PERCEPCION\s*DE\s*IVA\s*RG\s*333[^0-9]*(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE)
    rx_ret_iibb     = re.compile(r"RETENCION\s*DE\s*INGRESOS\s*BR[^0-9]*(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE)

    iva21_total = 0.0
    iva105_total = 0.0
    perc_total = 0.0
    ret_total = 0.0

    with pdfplumber.open(tmp) as pdf:
        for page in pdf.pages:
            text = (page.extract_text() or "").replace("−", "-")
            for m in rx_iva21_arancel.finditer(text):
                iva21_total += _to_float(m.group(1))
            for m in rx_minus_iva21.finditer(text):
                iva21_total += _to_float(m.group(1))
            for m in rx_iva105_costo.finditer(text):
                iva105_total += _to_float(m.group(1))
            for m in rx_perc_rg333.finditer(text):
                perc_total += _to_float(m.group(1))
            for m in rx_ret_iibb.finditer(text):
                ret_total += _to_float(m.group(1))

    base21 = round(iva21_total / 0.21, 2) if iva21_total else 0.0
    base105 = round(iva105_total / 0.105, 2) if iva105_total else 0.0

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
            round(iva21_total, 2),
            round(base105, 2),
            round(iva105_total, 2),
            round(perc_total, 2),
            round(ret_total, 2),
        ]
    })
    return resumen

def build_pdf(resumen_df: pd.DataFrame, out_path: str, titulo: str):
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    normal = styles["Normal"]
    h2 = styles["Heading2"]

    doc = SimpleDocTemplate(out_path, pagesize=A4)
    story = []
    story.append(Paragraph(titulo, title_style))
    story.append(Paragraph(f"Generado: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", normal))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Resumen de importes", h2))
    data = [["Concepto", "Monto ($)"]]
    for _, row in resumen_df.iterrows():
        data.append([row["Concepto"], _fmt(float(row["Monto"]))])

    tbl = Table(data, colWidths=[360, 140])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#222")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#f7f7f7"), colors.white]),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
        ("TOPPADDING", (0,0), (-1,0), 6),
    ]))
    story.append(tbl)

    story.append(Spacer(1, 24))
    story.append(Paragraph("AIE – Diseñado por Alfonso Alderete", normal))

    doc.build(story)
    return out_path
