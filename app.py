import os
import re
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st

from backend import extract_resumen_from_bytes, build_report_pdf, format_money


APP_TITLE = "IA AIE - Control Tarjetas Cabal"
PAGE_ICON = "logo_aie.jpg"
MAX_MB = 50


# =========================
# CUENTAS HOLISTOR
# =========================
# Completar con los códigos reales del plan de cuentas de Holistor.
CUENTAS_HOLISTOR = {
    "Neto al 21%": {
        "codigo": "CONFIGURAR",
        "cuenta": "Gastos / Aranceles Cabal al 21%",
    },
    "IVA al 21%": {
        "codigo": "CONFIGURAR",
        "cuenta": "IVA Crédito Fiscal 21%",
    },
    "Neto al 10,5%": {
        "codigo": "CONFIGURAR",
        "cuenta": "Gastos / Costo Financiero Cabal al 10,5%",
    },
    "IVA al 10,5%": {
        "codigo": "CONFIGURAR",
        "cuenta": "IVA Crédito Fiscal 10,5%",
    },
    "Percepción IVA": {
        "codigo": "CONFIGURAR",
        "cuenta": "Percepciones IVA",
    },
    "Retención IIBB": {
        "codigo": "CONFIGURAR",
        "cuenta": "Retenciones IIBB sufridas",
    },
    "Percepciones IIBB (SIRTAC)": {
        "codigo": "CONFIGURAR",
        "cuenta": "Percepciones IIBB SIRTAC",
    },
    "Contrapartida Cabal": {
        "codigo": "CONFIGURAR",
        "cuenta": "Tarjetas Cabal a Cobrar / Banco",
    },
}


def obtener_total_resumen(df: pd.DataFrame) -> float:
    if "Concepto" not in df.columns or "Monto Total" not in df.columns:
        return 0.0

    total_row = df[
        df["Concepto"].astype(str).str.upper().str.strip().eq("TOTAL")
    ]

    if not total_row.empty:
        return float(total_row.iloc[0]["Monto Total"])

    base = df[
        ~df["Concepto"].astype(str).str.upper().str.contains("TOTAL", na=False)
    ]

    return float(base["Monto Total"].sum())


def build_holistor_excel_bytes(df: pd.DataFrame) -> BytesIO:
    """
    Genera Excel base para Holistor.
    Estructura:
    - Conceptos al Debe
    - Contrapartida Cabal al Haber
    """

    fecha_asiento = datetime.now().strftime("%d/%m/%Y")
    nro_asiento = "0001"
    leyenda = "Liquidación Tarjetas Cabal"

    rows = []

    base = df.copy()
    base = base[
        ~base["Concepto"].astype(str).str.upper().str.strip().eq("TOTAL")
    ]

    for _, row in base.iterrows():
        concepto = str(row["Concepto"]).strip()
        monto = float(row["Monto Total"])

        if monto == 0:
            continue

        cuenta_info = CUENTAS_HOLISTOR.get(
            concepto,
            {
                "codigo": "CONFIGURAR",
                "cuenta": concepto,
            }
        )

        rows.append({
            "Fecha": fecha_asiento,
            "Nro Asiento": nro_asiento,
            "Código Cuenta": cuenta_info["codigo"],
            "Cuenta": cuenta_info["cuenta"],
            "Debe": round(monto, 2),
            "Haber": 0.00,
            "Concepto": concepto,
            "Leyenda": leyenda,
        })

    total = obtener_total_resumen(df)
    contra = CUENTAS_HOLISTOR["Contrapartida Cabal"]

    rows.append({
        "Fecha": fecha_asiento,
        "Nro Asiento": nro_asiento,
        "Código Cuenta": contra["codigo"],
        "Cuenta": contra["cuenta"],
        "Debe": 0.00,
        "Haber": round(total, 2),
        "Concepto": "Contrapartida Cabal",
        "Leyenda": leyenda,
    })

    holistor_df = pd.DataFrame(rows)

    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        holistor_df.to_excel(writer, sheet_name="Holistor", index=False)

        workbook = writer.book
        worksheet = writer.sheets["Holistor"]

        header_fmt = workbook.add_format({
            "bold": True,
            "bg_color": "#D9EAF7",
            "border": 1,
        })

        money_fmt = workbook.add_format({
            "num_format": "#,##0.00",
        })

        for col_num, value in enumerate(holistor_df.columns.values):
            worksheet.write(0, col_num, value, header_fmt)

        worksheet.set_column("A:A", 13)
        worksheet.set_column("B:B", 14)
        worksheet.set_column("C:C", 18)
        worksheet.set_column("D:D", 38)
        worksheet.set_column("E:F", 14, money_fmt)
        worksheet.set_column("G:G", 32)
        worksheet.set_column("H:H", 32)

        worksheet.freeze_panes(1, 0)

    output.seek(0)
    return output


st.set_page_config(
    page_title=APP_TITLE,
    page_icon=PAGE_ICON,
    layout="centered",
)


# =========================
# ENCABEZADO
# =========================
left, right = st.columns([1, 3])

with left:
    if os.path.exists(PAGE_ICON):
        st.image(PAGE_ICON, use_container_width=True)

with right:
    st.title(APP_TITLE)
    st.caption("Procesar liquidaciones automáticas de tarjetas Cabal")

st.markdown(
    '<hr style="margin:8px 0 20px 0;">',
    unsafe_allow_html=True,
)


# =========================
# CARGA DE PDF
# =========================
pdf_file = st.file_uploader(
    "📄 PDF de liquidación Cabal",
    type=["pdf"],
)


if pdf_file is None:
    st.info("Subí un PDF de liquidación Cabal para comenzar.")


if st.button("Procesar y generar informe", disabled=pdf_file is None):

    pdf_bytes = pdf_file.getvalue()
    size_mb = len(pdf_bytes) / (1024 * 1024)

    if size_mb > MAX_MB:
        st.error(f"El archivo supera {MAX_MB} MB.")

    else:
        with st.spinner("Procesando..."):

            # 1) Cálculos del backend
            resumen = extract_resumen_from_bytes(pdf_bytes)

            # 2) Ocultar solamente la fila "-IVA" de débitos al comercio
            mask_menos_iva = resumen["Concepto"].str.contains(
                r"^\s*[−-]\s*IVA\b",
                flags=re.IGNORECASE,
                regex=True,
                na=False,
            )

            resumen_filtrado = resumen.loc[
                ~mask_menos_iva
            ].reset_index(drop=True)

            # 3) Mostrar tabla en pantalla
            df_display = resumen_filtrado.copy()

            if "Monto Total" in df_display.columns:
                df_display["Monto Total"] = df_display["Monto Total"].apply(format_money)

            st.subheader("Resumen de importes")
            st.dataframe(df_display, use_container_width=True)

            # 4) Descargar PDF
            out_path = "IA_AIE_Resumen_de_Importes_Cabal.pdf"

            build_report_pdf(
                resumen_filtrado,
                out_path,
                titulo="Resumen de importes",
            )

            with open(out_path, "rb") as f:
                st.download_button(
                    "⬇️ Descargar informe PDF",
                    f,
                    file_name=out_path,
                    mime="application/pdf",
                )

            try:
                os.remove(out_path)
            except OSError:
                pass

            # 5) Descargar Excel Holistor
            excel_bytes = build_holistor_excel_bytes(resumen_filtrado)

            st.download_button(
                "⬇️ Descargar Excel formato Holistor",
                data=excel_bytes,
                file_name="IA_AIE_Cabal_Formato_Holistor.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
