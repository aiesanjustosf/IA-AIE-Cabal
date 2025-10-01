import streamlit as st
from backend import extract_resumen_from_bytes, build_report_pdf

st.set_page_config(page_title="IA AIE - Control Tarjeta Cabal Credicoop", page_icon="📄", layout="centered")
st.title("IA AIE - Control Tarjeta Cabal Credicoop")
st.caption("Subí el PDF y descargá el informe (solo resumen de importes).")

titulo = st.text_input("Título del informe", value="IA AIE - Control Tarjeta Cabal Credicoop")
pdf_file = st.file_uploader("📄 PDF de Cabal/Credicoop", type=["pdf"])

if st.button("✅ Procesar y generar informe") and pdf_file is not None:
    with st.spinner("Procesando..."):
        resumen = extract_resumen_from_bytes(pdf_file.getvalue())
        st.subheader("📊 Resumen")
        st.dataframe(resumen)

        out_path = "Informe_Cabal.pdf"
        build_report_pdf(resumen, out_path, titulo=titulo)

        with open(out_path, "rb") as f:
            st.download_button("⬇️ Descargar informe PDF", f, file_name="IA_AIE_Control_Tarjeta_Cabal_Credicoop.pdf", mime="application/pdf")
