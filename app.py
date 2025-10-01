import os
import re
import streamlit as st
from backend import extract_resumen_from_bytes, build_report_pdf, format_money  # usamos tu format_money

APP_TITLE = "IA AIE - Control Tarjeta Cabal Credicoop"
PAGE_ICON  = "logo_aie.jpg"  # asegurate de subir este archivo al repo
MAX_MB    = 50

st.set_page_config(page_title=APP_TITLE, page_icon=PAGE_ICON, layout="centered")

# Encabezado
left, right = st.columns([1, 3])
with left:
    if os.path.exists(PAGE_ICON):
        st.image(PAGE_ICON, use_container_width=True)
with right:
    st.title(APP_TITLE)
    st.caption("Subí el PDF y descargá el informe (solo resumen de importes).")

st.markdown('<hr style="margin:8px 0 20px 0;">', unsafe_allow_html=True)

pdf_file = st.file_uploader("📄 PDF de Cabal/Credicoop", type=["pdf"])

if st.button("✅ Procesar y generar informe") and pdf_file is not None:
    size_mb = len(pdf_file.getvalue()) / (1024 * 1024)
    if size_mb > MAX_MB:
        st.error(f"El archivo supera {MAX_MB} MB.")
    else:
        with st.spinner("Procesando..."):
            # 1) Usar TUS cálculos originales
            resumen = extract_resumen_from_bytes(pdf_file.getvalue())

            # 2) Ocultar SOLAMENTE la fila '-IVA (21% en Débitos al Comercio)'
            mask_menos_iva = resumen["Concepto"].str.contains(r"^-\\s*IVA", flags=re.IGNORECASE, regex=True)
            resumen_filtrado = resumen.loc[~mask_menos_iva].reset_index(drop=True)

            # 3) Mostrar tabla con separador de miles (en pantalla únicamente)
            df_display = resumen_filtrado.copy()
            df_display["Monto Total"] = df_display["Monto Total"].apply(format_money)

            st.subheader("Resumen de importes")
            st.dataframe(df_display, use_container_width=True)

            # 4) Generar PDF con el mismo filtrado y título pedido
            out_path = "IA_AIE_Resumen_de_Importes.pdf"
            build_report_pdf(resumen_filtrado, out_path, titulo="Resumen de importes")
            with open(out_path, "rb") as f:
                st.download_button("⬇️ Descargar informe PDF", f, file_name=out_path, mime="application/pdf")

            # Limpieza
            try:
                os.remove(out_path)
            except OSError:
                pass
