import re
import datetime
import pdfplumber
import pandas as pd

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def _to_float(s: str) -> float:
    return float(s.replace('.', '').replace(',', '.'))

def _fmt_money(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def extract_resumen_from_bytes(pdf_bytes: bytes) -> pd.DataFrame:
    tmp_path = "_aie_input.pdf"
    with open(tmp_path, "wb") as f:
        f.write(pdf_bytes)

    rx_iva21_arancel = re.compile(r"IVA\s*S/ARANCEL\s*DE\s*DESCUENTO\s*21,00%[^0-9]*(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE)
    rx_minus_iva21 = re.compile(r"[−-]\s*IVA\s*21,00%[^0-9]*(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE)
    rx_iva105_costo = re.compile(r"IVA\s*S/COSTO\s*FINANCIERO\s*10,50%[^0-9]*(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE)
    rx_perc_rg333 = re.compile(r"PERCEPCION\s*DE\s*IVA\s*RG\s*333[^0-9]*(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE)
    rx_ret_iibb = re.compile(r"RETENCION\s*DE\s*INGRESOS\s*BR[^0-9]*(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE)

    tot_iva_arancel = 0.0
    tot_iva_costo = 0.0
    tot_percep = 0.0
    tot_ret_ib = 0.0
    tot_menos_iva = 0.0

    with pdfplumber.open(tmp_path) as pdf:
        for page in pdf.pages:
            txt = (page.extract_text() or "").replace("−", "-")
            for m in rx_iva21_arancel.finditer(txt):
                tot_iva_arancel += _to_float(m.group(1))
            for m in rx_minus_iva21.finditer(txt):
                tot_menos_iva += _to_float(m.group(1))
            for m in rx_iva105_costo.finditer(txt):
                tot_iva_costo += _to_float(m.group(1))
            for m in rx_perc_rg333.finditer(txt):
                tot_percep += _to_float(m.group(1))
            for m in rx_ret_iibb.finditer(txt):
                tot_ret_ib += _to_float(m.group(1))

    tot_iva_21_final = tot_iva_arancel + tot_menos_iva
    base_arancel = round(tot_iva_21_final / 0.21, 2) if tot_iva_21_final else 0.0
    base_costo = round(tot_iva_costo / 0.105, 2) if tot_iva_costo else 0.0

    resumen = pd.DataFrame({
        "Concepto": [
            "Base Neto Arancel (21%)",
            "IVA 21% sobre Arancel (incluye -IVA)",
            "Base Neto Costo Financiero (10,5%)",
            "IVA 10,5% sobre Costo Financiero",
            "Percepciones IVA RG 333",
            "Retenciones de Ingresos Brutos",
        ],
        "Monto Total": [
            round(base_arancel, 2),
            round(tot_iva_21_final, 2),
            round(base_costo, 2),
            round(tot_iva_costo, 2),
            round(tot_percep, 2),
            round(tot_ret_ib, 2),
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
        data.append([row["Concepto"], _fmt_money(float(row["Monto Total"]))])

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

    # Sin firma (pedido explícito)

    doc.build(story)
    return out_path
