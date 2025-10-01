
import streamlit as st, os
from backend import extract_summary, build_pdf

TITLE = "IA AIE - Control Tarjeta Cabal Credicoop"
MAX_MB = 50

st.set_page_config(page_title=TITLE, page_icon="logo_aie.jpg", layout="centered")

left, right = st.columns([1,3])
with left:
    st.image("logo_aie.jpg", use_container_width=True)
with right:
    st.title(TITLE)
    st.caption("No subas documentos con datos sensibles. El procesamiento es temporal y no se guarda ningún archivo en servidores propios.")

st.markdown('<hr style="margin:8px 0 20px 0;">', unsafe_allow_html=True)

pdf_file = st.file_uploader("PDF de Cabal/Credicoop", type=["pdf"])

if st.button("Procesar y generar informe") and pdf_file is not None:
    size_mb = len(pdf_file.getvalue()) / (1024*1024)
    if size_mb > MAX_MB:
        st.error(f"El archivo supera {MAX_MB} MB.")
    else:
        with st.spinner("Procesando..."):
            resumen = extract_summary(pdf_file.getvalue())
            df_show = resumen.copy()
            df_show["Monto"] = df_show["Monto"].apply(lambda v: f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.subheader("Resumen de importes (6 ítems)")
            st.dataframe(df_show, use_container_width=True)

            out_path = "IA_AIE_Control_Tarjeta_Cabal_Credicoop.pdf"
            build_pdf(resumen, out_path, titulo=TITLE)
            with open(out_path, "rb") as f:
                st.download_button("⬇️ Descargar informe PDF", f, file_name=out_path, mime="application/pdf")

            try:
                os.remove("_aie_input.pdf")
                os.remove(out_path)
            except OSError:
                pass
