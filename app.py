import os
import re
import streamlit as st
from backend import extract_summary, build_pdf

TITLE = "IA AIE - Control Tarjeta Cabal Credicoop"
MAX_MB = 50

st.set_page_config(page_title=TITLE, page_icon="logo_aie.jpg", layout="centered")

# Encabezado con logo
left, right = st.columns([1, 3])
with left:
    if os.path.exists("logo_aie.jpg"):
        st.image("logo_aie.jpg", use_container_width=True)
with right:
    st.title(TITLE)
    st.caption(
        "No subas documentos con datos sensibles. El procesamiento es temporal y no se guarda ningún archivo en servidores propios."
    )

st.markdown('<hr style="margin:8px 0 20px 0;">', unsafe_allow_html=True)

pdf_file = st.file_uploader("PDF de Cabal/Credicoop", type=["pdf"])

if st.button("Procesar y generar informe") and pdf_file is not None:
    size_mb = len(pdf_file.getvalue()) / (1024 * 1024)
    if size_mb > MAX_MB:
        st.error(f"El archivo supera {MAX_MB} MB.")
    else:
        with st.spinner("Procesando..."):
            resumen = extract_summary(pdf_file.getvalue())

            # 🔹 Filtrar fuera la fila '-IVA ...'
            mask_menos_iva = resumen["Concepto"].str.contains(
                r"-\s*IVA", flags=re.IGNORECASE, regex=True
            )
            resumen = resumen.loc[~mask_menos_iva].reset_index(drop=True)

            # Mostrar tabla
            st.subheader("Resumen de importes")
            st.dataframe(resumen, use_container_width=True)

            # Generar PDF
            out_path = "IA_AIE_Resumen_de_Importes.pdf"
            build_pdf(resumen, out_path, titulo="Resumen de importes")
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
