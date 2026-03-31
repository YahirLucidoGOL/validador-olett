import streamlit as st
import pdfplumber
import re
import pandas as pd
import zipfile
import io

# 1. Configuración de la plataforma Olett
st.set_page_config(page_title="Olett Auditor Pro", page_icon="🦉", layout="wide")

st.title("🦉 Auditoría de Precisión Olett")
st.markdown("### Triple Validación: RFC, Periodo y Número de Operación")
st.info("Sube archivos PDF (Detalle/Acuse), carpetas ZIP o archivos 'Todo en Uno'.")

# 2. Cargador de archivos (PDF y ZIP)
archivos_subidos = st.file_uploader("Arrastra tus archivos aquí", type=["pdf", "zip"], accept_multiple_files=True)

def extraer_info_sat(texto):
    """Motor de búsqueda flexible para documentos del SAT"""
    texto_limpio = texto.replace('\n', ' ')
    datos = {}
    
    # A. Búsqueda de Número de Operación (Regex flexible para acentos y puntos)
    # Basado en formato real: 'Número de operación: 266440003547'
    op_match = re.search(r'N[ÚU]MERO DE OPERACI[ÓO]N[:\s]*(\d+)', texto_limpio, re.IGNORECASE)
    datos['Operacion'] = op_match.group(1) if op_match else "N/A"
    
    # B. RFC (Patrón estándar de 12-13 caracteres)
    rfc_match = re.search(r'[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}', texto_limpio)
    datos['RFC'] = rfc_match.group() if rfc_match else "No encontrado"
    
    # C. Periodo (Mes y Año)
    per_match = re.search(r'PERIODO:\s*([A-Z\s]+20\d{2})', texto_limpio)
    datos['Periodo'] = per_match.group(1).strip() if per_match else "N/A"
    
    # D. Identificación de Tipo de Documento
    tiene_acuse = "ACUSE DE RECIBO" in texto_limpio
    tiene_detalle = "DETERMINACIÓN" in texto_limpio or "INGRESOS" in texto_limpio
    
    datos['Es_Ambos'] = tiene_acuse and tiene_detalle
    datos['Tipo'] = "ACUSE" if tiene_acuse else "DETALLE"

    # E. Extracción de saldos (EXCLUSIVO DEL ACUSE)
    if tiene_acuse:
        # IVA (Busca 'Cantidad a pagar' después de mencionar el impuesto)
        iva = re.search(r'IMPUESTO AL VALOR AGREGADO.*?CANTIDAD A PAGAR.*?([\d,]+)', texto_limpio)
        datos['IVA'] = f"${iva.group(1)}" if iva else "$0"
        
        # ISR Retenciones por salarios
        isr = re.search(r'RETENCIONES POR SALARIOS.*?CANTIDAD A PAGAR.*?([\d,]+)', texto_limpio)
        datos['ISR_Ret'] = f"${isr.group(1)}" if isr else "$0"
        
        # Total a Pagar (El de la línea de captura)
        total = re.search(r'TOTAL A PAGAR.*?([\d,]+)', texto_limpio)
        datos['Total'] = f"${total.group(1)}" if total else "$0"
        
    return datos

if archivos_subidos:
    grupos = {}
    
    for arc in archivos_subidos:
        docs_a_procesar = []
        # Si es ZIP, extraemos los PDFs internos
        if arc.name.endswith('.zip'):
            with zipfile.ZipFile(arc) as z:
                for f in z.namelist():
                    if f.endswith('.pdf'):
                        docs_a_procesar.append(io.BytesIO(z.read(f)))
        else:
            docs_a_procesar.append(arc)

        # Procesamos cada PDF individualmente
        for doc in docs_a_procesar:
            with pdfplumber.open(doc) as pdf:
                texto_full = "".join([p.extract_text().upper() for p in pdf.pages if p.extract_text()])
            
            info = extraer_info_sat(texto_full)
            op = info['Operacion']
            
            if op not in grupos:
                grupos[op] = {'DETALLE': None, 'ACUSE': None}
            
            # Si el archivo contiene ambos (Caso Yahir), llena las dos casillas de una vez
            if info['Es_Ambos']:
                grupos[op]['DETALLE'] = info
                grupos[op]['ACUSE'] = info
            else:
                grupos[op][info['Tipo']] = info

    # 3. Presentación de Resultados y Auditoría
    for op, docs in grupos.items():
        if op == "N/A":
            st.error("❌ No se detectó Número de Operación en uno de los archivos.")
            continue
            
        st.subheader(f"📑 Análisis de Operación: {op}")
        det, acu = docs['DETALLE'], docs['ACUSE']
        
        if det and acu:
            # VALIDACIÓN TRIPLE: RFC, PERIODO Y OPERACIÓN
            match_rfc = (det['RFC'] == acu['RFC'])
            match_periodo = (det['Periodo'] == acu['Periodo'])
            
            if match_rfc and match_periodo:
                st.success(f"✅ CONCILIACIÓN EXITOSA: {acu['RFC']} - {acu['Periodo']}")
                
                # Métricas extraídas del Acuse
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("IVA (Acuse)", acu['IVA'])
                with c2:
                    st.metric("ISR Retenciones", acu['ISR_Ret'])
                with c3:
                    st.metric("Total a Pagar (Línea)", acu['Total'])
            else:
                st.error("❌ DISCREPANCIA DETECTADA: El RFC o Periodo no coinciden entre documentos.")
                st.write(f"RFC Detalle: {det['RFC']} vs Acuse: {acu['RFC']}")
                st.write(f"Periodo Detalle: {det['Periodo']} vs Acuse: {acu['Periodo']}")
        else:
            tipo_falta = "ACUSE" if not acu else "DETALLE"
            st.warning(f"⚠️ Operación {op} incompleta. Falta subir el {tipo_falta}.")

st.divider()
st.caption("Tecnología Desarrollada para Despacho Olett - Auditoría Automatizada 2026")