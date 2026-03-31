import streamlit as st
import pdfplumber
import re
import pandas as pd
import zipfile
import io

# 1. Configuración de la plataforma Olett
st.set_page_config(page_title="Olett Auditor Pro", page_icon="🦉", layout="wide")

st.title("🦉 Auditoría de Precisión Olett")
st.markdown("### Triple Validación: RFC, Periodo y Operación")

archivos_subidos = st.file_uploader("Sube tus PDFs o ZIPs", type=["pdf", "zip"], accept_multiple_files=True)

def extraer_info_sat(texto):
    """Buscador de alta precisión diseñado para documentos combinados del SAT"""
    # Limpieza profunda de espacios y saltos de línea
    texto_limpio = re.sub(r'\s+', ' ', texto).upper()
    datos = {}
    
    # A. BÚSQUEDA DEL NÚMERO DE OPERACIÓN (Ej: 266440003547)
    op_match = re.search(r'N[ÚU]MERO\s*DE\s*OPERACI[ÓO]N.*?\s*(\d{10,14})', texto_limpio)
    datos['Operacion'] = op_match.group(1) if op_match else "N/A"
    
    # B. RFC (Identidad: MDA0904078Z2)
    rfc_match = re.search(r'[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}', texto_limpio)
    datos['RFC'] = rfc_match.group() if rfc_match else "No encontrado"
    
    # C. PERIODO (Enero 2026)
    per_match = re.search(r'PERIODO:\s*([A-Z\s]+20\d{2})', texto_limpio)
    datos['Periodo'] = per_match.group(1).strip() if per_match else "N/A"
    
    # D. CLASIFICACIÓN ULTRA-SENSIBLE
    # El acuse tiene línea de captura; el detalle tiene ingresos nominales
    tiene_acuse = any(x in texto_limpio for x in ["ACUSE DE RECIBO", "LÍNEA DE CAPTURA"])
    tiene_detalle = any(x in texto_limpio for x in ["INGRESOS NOMINALES", "DETERMINACIÓN", "ISR PERSONAS MORALES"])
    
    datos['Tiene_Acuse'] = tiene_acuse
    datos['Tiene_Detalle'] = tiene_detalle

    if tiene_acuse:
        # Extracción de montos del Acuse con saltos de ruido
        iva = re.search(r'IMPUESTO\s*AL\s*VALOR\s*AGREGADO.*?CANTIDAD\s*A\s*PAGAR.*?([\d,]+)', texto_limpio)
        datos['IVA'] = f"${iva.group(1)}" if iva else "$0"
        
        isr = re.search(r'RETENCIONES\s*POR\s*SALARIOS.*?CANTIDAD\s*A\s*PAGAR.*?([\d,]+)', texto_limpio)
        datos['ISR_Ret'] = f"${isr.group(1)}" if isr else "$0"
        
        total = re.search(r'TOTAL\s*A\s*PAGAR.*?([\d,]+)', texto_limpio)
        datos['Total'] = f"${total.group(1)}" if total else "$0"
        
    return datos

if archivos_subidos:
    grupos = {}
    
    for arc in archivos_subidos:
        docs_a_procesar = []
        if arc.name.endswith('.zip'):
            with zipfile.ZipFile(arc) as z:
                for f in z.namelist():
                    if f.endswith('.pdf'): docs_a_procesar.append(io.BytesIO(z.read(f)))
        else:
            docs_a_procesar.append(arc)

        for doc in docs_a_procesar:
            with pdfplumber.open(doc) as pdf:
                texto_full = ""
                for p in pdf.pages:
                    txt = p.extract_text()
                    if txt: texto_full += txt + " "
            
            info = extraer_info_sat(texto_full)
            op = info['Operacion']
            
            if op not in grupos:
                grupos[op] = {'DETALLE': None, 'ACUSE': None}
            
            # Si el archivo tiene la parte de Acuse, lo guardamos
            if info['Tiene_Acuse']:
                grupos[op]['ACUSE'] = info
            # Si el archivo tiene la parte de Detalle, lo guardamos (puede ser el mismo archivo)
            if info['Tiene_Detalle']:
                grupos[op]['DETALLE'] = info

    # 3. Presentación de Resultados
    for op, docs in grupos.items():
        if op == "N/A":
            st.error("❌ El sistema no pudo detectar el folio de operación.")
            continue
            
        st.subheader(f"📑 Operación: {op}")
        det, acu = docs['DETALLE'], docs['ACUSE']
        
        if det and acu:
            # Validación Final
            if det['RFC'] == acu['RFC'] and det['Periodo'] == acu['Periodo']:
                st.success(f"✅ CONCILIACIÓN EXITOSA: {acu['RFC']} - {acu['Periodo']}")
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("IVA (Acuse)", acu['IVA'])
                with c2: st.metric("ISR Retenciones", acu['ISR_Ret'])
                with c3: st.metric("Total a Pagar (Línea)", acu['Total'])
            else:
                st.error(f"❌ DISCREPANCIA: RFC ({det['RFC']} vs {acu['RFC']}) o Periodo no coinciden.")
        else:
            falta = "el Detalle" if not det else "el Acuse"
            st.warning(f"⚠️ Operación {op} incompleta. No se detectó {falta} en los archivos subidos.")

st.divider()
st.caption("Olett Auditoría Automatizada - 2026")