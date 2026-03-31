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

archivos_subidos = st.file_uploader("Sube tus PDFs o ZIPs", type=["pdf", "zip"], accept_multiple_files=True)

def extraer_info_sat(texto):
    """Buscador ultra-flexible para documentos del SAT"""
    # Limpiamos el texto eliminando ruidos comunes de tablas
    texto_limpio = texto.replace('\n', ' ').replace('"', '')
    datos = {}
    
    # A. Búsqueda de Número de Operación (Ahora ignora comas y símbolos intermedios)
    # Buscamos 'Número de operación', saltamos lo que no sea dígito, y capturamos los números
    op_match = re.search(r'N[ÚU]MERO DE OPERACI[ÓO]N[^\d]*(\d+)', texto_limpio, re.IGNORECASE)
    datos['Operacion'] = op_match.group(1) if op_match else "N/A"
    
    # B. RFC
    rfc_match = re.search(r'[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}', texto_limpio)
    datos['RFC'] = rfc_match.group() if rfc_match else "No encontrado"
    
    # C. Periodo
    per_match = re.search(r'PERIODO:\s*([A-Z\s]+20\d{2})', texto_limpio)
    datos['Periodo'] = per_match.group(1).strip() if per_match else "N/A"
    
    # D. Identificación de Tipo
    tiene_acuse = "ACUSE DE RECIBO" in texto_limpio
    tiene_detalle = "DETERMINACIÓN" in texto_limpio or "INGRESOS" in texto_limpio
    
    datos['Es_Ambos'] = tiene_acuse and tiene_detalle
    datos['Tipo'] = "ACUSE" if tiene_acuse else "DETALLE"

    if tiene_acuse:
        # Búsqueda de montos con flexibilidad para tablas
        iva = re.search(r'IMPUESTO AL VALOR AGREGADO[^\d]*CANTIDAD A PAGAR[^\d]*([\d,]+)', texto_limpio)
        datos['IVA'] = f"${iva.group(1)}" if iva else "$0"
        
        isr = re.search(r'RETENCIONES POR SALARIOS[^\d]*CANTIDAD A PAGAR[^\d]*([\d,]+)', texto_limpio)
        datos['ISR_Ret'] = f"${isr.group(1)}" if isr else "$0"
        
        total = re.search(r'TOTAL A PAGAR[^\d]*([\d,]+)', texto_limpio)
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
                texto_full = "".join([p.extract_text().upper() for p in pdf.pages if p.extract_text()])
            
            info = extraer_info_sat(texto_full)
            op = info['Operacion']
            
            if op not in grupos:
                grupos[op] = {'DETALLE': None, 'ACUSE': None}
            
            if info['Es_Ambos']:
                grupos[op]['DETALLE'] = info
                grupos[op]['ACUSE'] = info
            else:
                grupos[op][info['Tipo']] = info

    for op, docs in grupos.items():
        if op == "N/A":
            st.error("❌ No se detectó Número de Operación en uno de los archivos. Verifique el formato.")
            continue
            
        st.subheader(f"📑 Operación: {op}")
        det, acu = docs['DETALLE'], docs['ACUSE']
        
        if det and acu:
            if det['RFC'] == acu['RFC'] and det['Periodo'] == acu['Periodo']:
                st.success(f"✅ CONCILIACIÓN EXITOSA: {acu['RFC']} - {acu['Periodo']}")
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("IVA (Acuse)", acu['IVA'])
                with c2: st.metric("ISR Retenciones", acu['ISR_Ret'])
                with c3: st.metric("Línea de Captura", acu['Total'])
            else:
                st.error("❌ DISCREPANCIA: RFC o Periodo no coinciden.")
        else:
            st.warning(f"⚠️ Falta completar la pareja para la operación {op}.")

st.divider()
st.caption("Desarrollado para Despacho Olett - 2026")