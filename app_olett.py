import streamlit as st
import pdfplumber
import re
import pandas as pd
import zipfile
import io

# 1. Configuración de Olett
st.set_page_config(page_title="Olett Auditor Pro", page_icon="🦉", layout="wide")

st.title("🦉 Auditoría de Precisión Olett")
st.markdown("### Triple Validación: RFC, Periodo y Operación")

archivos_subidos = st.file_uploader("Sube tus PDFs o ZIPs", type=["pdf", "zip"], accept_multiple_files=True)

def extraer_info_sat(texto):
    """Buscador de ultra-precisión para el formato extendido del SAT"""
    # Limpieza profunda de espacios
    texto_limpio = re.sub(r'\s+', ' ', texto).upper()
    datos = {}
    
    # A. NÚMERO DE OPERACIÓN
    op_match = re.search(r'N[ÚU]MERO\s*DE\s*OPERACI[ÓO]N[^\d]*(\d{10,14})', texto_limpio)
    datos['Operacion'] = op_match.group(1) if op_match else "N/A"
    
    # B. RFC
    rfc_match = re.search(r'[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}', texto_limpio)
    datos['RFC'] = rfc_match.group() if rfc_match else "No encontrado"
    
    # C. PERIODO (Unión de Mes y Ejercicio)
    mes_match = re.search(r'PER[ÍI]ODO\s*DE\s*LA\s*DECLARACI[ÓO]N[:\s]*([A-Z]+)', texto_limpio)
    ejercicio_match = re.search(r'EJERCICIO[:\s]*(\d{4})', texto_limpio)
    if mes_match and ejercicio_match:
        datos['Periodo'] = f"{mes_match.group(1).strip()} {ejercicio_match.group(1)}"
    else:
        per_alt = re.search(r'PERIODO:\s*([A-Z\s]+20\d{2})', texto_limpio)
        datos['Periodo'] = per_alt.group(1).strip() if per_alt else "N/A"
    
    # D. CLASIFICACIÓN
    tiene_acuse = any(x in texto_limpio for x in ["ACUSE DE RECIBO", "LÍNEA DE CAPTURA"])
    tiene_detalle = any(x in texto_limpio for x in ["INGRESOS NOMINALES", "DETERMINACIÓN", "ISR PERSONAS MORALES"])
    
    datos['Tiene_Acuse'] = tiene_acuse
    datos['Tiene_Detalle'] = tiene_detalle

    if tiene_acuse:
        # E. EXTRACCIÓN DE MONTOS
        
        # IVA
        iva = re.search(r'IMPUESTO\s*AL\s*VALOR\s*AGREGADO.*?CANTIDAD\s*A\s*PAGAR.*?([\d,]+)', texto_limpio)
        datos['IVA'] = f"${iva.group(1)}" if iva else "$0"
        
        # ISR Retenciones
        isr = re.search(r'RETENCIONES\s*POR\s*SALARIOS.*?CANTIDAD\s*A\s*PAGAR.*?([\d,]+)', texto_limpio)
        datos['ISR_Ret'] = f"${isr.group(1)}" if isr else "$0"
        
        # TOTAL A PAGAR (Sección Línea de Captura)
        # Buscamos "IMPORTE TOTAL A PAGAR", saltamos cualquier cosa hasta encontrar el primer número (ignorando el $)
        total_final = re.search(r'IMPORTE\s*TOTAL\s*A\s*PAGAR.*?\s*\$?\s*([\d,]{3,})', texto_limpio)
        if total_final:
            datos['Total'] = f"${total_final.group(1)}"
        else:
            # Intento alternativo por si no trae la palabra "Importe"
            total_alt = re.search(r'TOTAL\s*A\s*PAGAR.*?\s*\$?\s*([\d,]{3,})', texto_limpio)
            datos['Total'] = f"${total_alt.group(1)}" if total_alt else "$0"
        
    return datos

if archivos_subidos:
    grupos = {}
    for arc in archivos_subidos:
        docs = []
        if arc.name.endswith('.zip'):
            with zipfile.ZipFile(arc) as z:
                for f in z.namelist():
                    if f.endswith('.pdf'): docs.append(io.BytesIO(z.read(f)))
        else: docs.append(arc)

        for doc in docs:
            with pdfplumber.open(doc) as pdf:
                texto_full = " ".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            
            info = extraer_info_sat(texto_full)
            op = info['Operacion']
            if op not in grupos: grupos[op] = {'DETALLE': None, 'ACUSE': None}
            if info['Tiene_Acuse']: grupos[op]['ACUSE'] = info
            if info['Tiene_Detalle']: grupos[op]['DETALLE'] = info

    for op, docs in grupos.items():
        if op == "N/A": continue
        st.subheader(f"📑 Operación: {op}")
        det, acu = docs['DETALLE'], docs['ACUSE']
        
        if det and acu:
            if det['RFC'] == acu['RFC'] and det['Periodo'] == acu['Periodo']:
                st.success(f"✅ CONCILIACIÓN EXITOSA: {acu['RFC']} - {acu['Periodo']}")
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("IVA (Acuse)", acu['IVA'])
                with c2: st.metric("ISR Retenciones", acu['ISR_Ret'])
                with c3: st.metric("Total a Pagar (Línea)", acu['Total'])
            else:
                st.error(f"❌ DISCREPANCIA: RFC o Periodo no coinciden.")
        else:
            st.warning(f"⚠️ Operación {op} incompleta.")

st.divider()
st.caption("Olett Auditoría Automatizada - 2026")