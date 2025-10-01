AIE - Patch de backend (drop-in)

Este ZIP contiene SOLO el `backend.py` corregido para tu app Streamlit.

Qué cambia:
- El informe de resumen ya NO muestra la fila "-IVA (21% en Débitos al Comercio)".
- Ese importe se suma dentro de "IVA 21% sobre Arancel".
- Se mantienen exactamente 6 filas en el informe.
- Formato numérico: miles con punto y decimales con coma.
- Sin firma en el PDF.

Cómo aplicar:
1) En tu repositorio de la app, reemplazá `backend.py` por el de este ZIP.
2) Verificá que tu `app.py` tenga el favicon: st.set_page_config(page_icon="logo_aie.jpg").
3) Redeploy (o Rerun) en Streamlit Cloud.
