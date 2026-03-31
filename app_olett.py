import streamlit as st
import pdfplumber
import re

# Configuración de la página
st.set_page_config(page_title="Olett - Validador Fiscal", page_icon="🦉")

st.title("🦉 Olett: Validador de Opiniones SAT")
st.markdown("Sube uno o varios PDFs para validar el cumplimiento fiscal automáticamente.")

# 1. Cargador de archivos
archivos_subidos = st.file_uploader("Arrastra aquí tus PDFs", type="pdf", accept_multiple_files=True)

if archivos_subidos:
    resultados = []
    
    for archivo in archivos_subidos:
        with pdfplumber.open(archivo) as pdf:
            texto_completo = ""
            for pagina in pdf.pages:
                texto_completo += pagina.extract_text().upper()
            
            # Buscamos RFC
            rfc_pattern = r'[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}'
            rfc_match = re.search(rfc_pattern, texto_completo)
            rfc = rfc_match.group() if rfc_match else "No detectado"
            
            # Buscamos Estatus
            status = "DESCONOCIDO"
            if "POSITIV" in texto_completo:
                status = "✅ POSITIVA"
            elif "NEGATIV" in texto_completo:
                status = "❌ NEGATIVA"
            
            resultados.append({"Archivo": archivo.name, "RFC": rfc, "Estatus": status})

    # 2. Mostrar resultados en una tabla pro
    st.table(resultados)
    
    # 3. Botón para descargar reporte (opcional)
    if st.button("Generar Reporte para Olett"):
        st.success("Reporte listo para tu base de datos.")