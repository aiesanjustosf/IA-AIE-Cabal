import os
import re
import datetime
import pdfplumber
import pandas as pd

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def to_float(s: str) -> float:
    """
    Convierte importes argentinos tipo 1.234,56 a float.
    """
    if s is None:
        return 0.0

    s = str(s).strip()
    s = s.replace("−", "-")
    s = s.replace("-", "")
    s = s.replace(".", "")
    s = s.replace(",", ".")

    try:
        return float(s)
    except ValueError:
        return 0.0


def extract_resumen_from_bytes(pdf_bytes: bytes):
    tmp_path = "_input.pdf"

    with open(tmp_path, "wb") as f:
        f.write(pdf_bytes)

    patterns = {
        # IVA 21% sobre arancel
        "IVA_ARANCEL_21": re.compile(
            r"IVA\s+S/ARANCEL\s+DE\s+DESCUENTO\s+21,00%.*?([\d.]+,\d{2})\s*[-−]",
            re.IGNORECASE,
        ),

        # IVA 10,5% sobre costo financiero
        "IVA_COSTO_10_5": re.compile(
            r"IVA\s+S/COSTO\s+FINANCIERO\s+10,50%.*?([\d.]+,\d{2})\s*[-−]",
            re.IGNORECASE,
        ),

        # Percepciones IVA RG 333
        "PERCEPCION_RG333": re.compile(
            r"PERCEPCION\s+DE\s+IVA\s+RG\s+333.*?([\d.]+,\d{2})\s*[-−]",
            re.IGNORECASE,
        ),

        # Retenciones reales de Ingresos Brutos
        # Ejemplo: RETENCION DE INGRESOS BR 3,60% 313.134,00 11.272,82-
        "RETENCION_IB": re.compile(
            r"RETENCION\s+DE\s+INGRESOS\s+BR(?:UTOS)?\b.*?([\d.]+,\d{2})\s*[-−]",
            re.IGNORECASE,
        ),

        # Percepciones IIBB SIRTAC
        # Ejemplo: RETENCION IIBB SIRTAC 0,10% 173.068,02 173,07-
        "PERCEPCION_IIBB_SIRTAC": re.compile(
            r"RETENCION\s+IIBB\s+SIRTAC\b.*?([\d.]+,\d{2})\s*[-−]",
            re.IGNORECASE,
        ),

        # IVA de débitos al comercio
        # Esta fila después la ocultás desde app.py, como ya venís haciendo.
        "MENOS_IVA_21": re.compile(
            r"[-−]IVA\s+21,00%.*?([\d.]+,\d{2})\s*[-−]",
            re.IGNORECASE,
        ),
    }

    rows = []

    try:
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                text = text.replace("−", "-")

                for key, rx in patterns.items():
                    for m in rx.finditer(text):
                        rows.append({
                            "Concepto": key,
                            "Importe Total": to_float(m.group(1)),
                        })

    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    df = pd.DataFrame(rows, columns=["Concepto", "Importe Total"])

    def suma(conc: str) -> float:
        return df.loc[df["Concepto"] == conc, "Importe Total"].sum()

    tot_iva_arancel = suma("IVA_ARANCEL_21")
    tot_iva_costo = suma("IVA_COSTO_10_5")
    tot_percep_iva = suma("PERCEPCION_RG333")
    tot_ret_ib = suma("RETENCION_IB")
    tot_percep_iibb_sirtac = suma("PERCEPCION_IIBB_SIRTAC")
    tot_menos_iva = suma("MENOS_IVA_21")

    base_arancel = tot_iva_arancel / 0.21 if tot_iva_arancel else 0
    base_costo = tot_iva_costo / 0.105 if tot_iva_costo else 0

    return pd.DataFrame({
        "Concepto": [
            "Base Neto Arancel",
            "IVA 21% sobre Arancel",
            "Base Neto Costo Financiero",
            "IVA 10,5% sobre Costo Financiero",
            "-IVA (21% en Débitos al Comercio)",
            "Percepciones IVA RG 333",
            "Retenciones de Ingresos Brutos",
            "Percepciones IIBB (SIRTAC)",
        ],
        "Monto Total": [
            round(base_arancel, 2),
            round(tot_iva_arancel, 2),
            round(base_costo, 2),
            round(tot_iva_costo, 2),
            round(tot_menos_iva, 2),
            round(tot_percep_iva, 2),
            round(tot_ret_ib, 2),
            round(tot_percep_iibb_sirtac, 2),
        ],
    })


def format_money(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_report_pdf(
    resumen_df: pd.DataFrame,
    out_path: str,
    titulo: str = "IA AIE - Control Tarjetas Cabal",
):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(out_path, pagesize=A4)

    story = []

    story.append(Paragraph(titulo, styles["Title"]))
    story.append(
        Paragraph(
            f"Generado: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 12))

    story.append(Paragraph("Resumen de importes", styles["Heading2"]))

    data_table = [["Concepto", "Monto Total ($)"]]

    for _, row in resumen_df.iterrows():
        data_table.append([
            row["Concepto"],
            format_money(row["Monto Total"]),
        ])

    tbl = Table(data_table, colWidths=[350, 150])

    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.HexColor("#f7f7f7"),
            colors.white,
        ]),
    ]))

    story.append(tbl)
    doc.build(story)

    return out_path
