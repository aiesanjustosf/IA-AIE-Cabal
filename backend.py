import re, datetime, pdfplumber, pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def to_float(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))

def extract_resumen_from_bytes(pdf_bytes: bytes):
    tmp_path = "_input.pdf"
    with open(tmp_path, "wb") as f:
        f.write(pdf_bytes)

    patterns = {
        "IVA_ARANCEL_21": re.compile(r"IVA S/ARANCEL DE DESCUENTO\s+21,00%[^\n\r]*?([\d.]+,\d{2})\s*[-−]"),
        "IVA_COSTO_10_5": re.compile(r"IVA S/COSTO FINANCIERO\s+10,50%[^\n\r]*?([\d.]+,\d{2})\s*[-−]"),
        "PERCEPCION_RG333": re.compile(r"PERCEPCION DE IVA RG 333[^\n\r]*?([\d.]+,\d{2})\s*[-−]"),
        "RETENCION_IB": re.compile(r"RETENCION DE INGRESOS BR[^\n\r]*?([\d.]+,\d{2})\s*[-−]"),
        "MENOS_IVA_21": re.compile(r"[-−]IVA\s+21,00%[^\n\r]*?([\d.]+,\d{2})\s*[-−]"),
    }

    rows = []
    with pdfplumber.open(tmp_path) as pdf:
        for page in pdf.pages:
            text = (page.extract_text() or "").replace("−", "-")
            for key, rx in patterns.items():
                for m in rx.finditer(text):
                    rows.append({"Concepto": key, "Importe Total": to_float(m.group(1))})

    df = pd.DataFrame(rows)

    def suma(conc):
        try:
            return float(df.loc[df["Concepto"] == conc, "Importe Total"].sum())
        except Exception:
            return 0.0

    tot_iva_arancel = suma("IVA_ARANCEL_21")
    tot_iva_costo   = suma("IVA_COSTO_10_5")
    tot_percep      = suma("PERCEPCION_RG333")
    tot_ret_ib      = suma("RETENCION_IB")
    tot_menos_iva   = suma("MENOS_IVA_21")

    base_arancel = tot_iva_arancel / 0.21 if tot_iva_arancel else 0.0
    base_costo   = tot_iva_costo / 0.105 if tot_iva_costo else 0.0

    resumen = pd.DataFrame({
        "Concepto": [
            "Base Neto Arancel",
            "IVA 21% sobre Arancel",
            "Base Neto Costo Financiero",
            "IVA 10,5% sobre Costo Financiero",
            "-IVA (21% en Débitos al Comercio)",
            "Percepciones IVA RG 333",
            "Retenciones de Ingresos Brutos",
        ],
        "Monto Total": [
            round(base_arancel, 2),
            round(tot_iva_arancel, 2),
            round(base_costo, 2),
            round(tot_iva_costo, 2),
            round(tot_menos_iva, 2),
            round(tot_percep, 2),
            round(tot_ret_ib, 2),
        ]
    })
    return resumen

def format_money(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def build_report_pdf(resumen_df: pd.DataFrame, out_path: str, titulo: str = "IA AIE - Control Tarjeta Cabal Credicoop"):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(out_path, pagesize=A4)
    story = []
    story.append(Paragraph(titulo, styles["Title"]))
    story.append(Paragraph(f"Generado: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Resumen de importes", styles["Heading2"]))
    data_table = [["Concepto", "Monto Total ($)"]] + [[c, format_money(m)] for c, m in resumen_df.values]
    tbl = Table(data_table, colWidths=[350, 150])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#222222")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#f7f7f7"), colors.white]),
    ]))
    story.append(tbl)
    doc.build(story)
    return out_path
