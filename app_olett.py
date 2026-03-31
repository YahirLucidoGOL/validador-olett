import streamlit as st
import pdfplumber
import re
import pandas as pd

# 1. Configuración visual pro para Olett
st.set_page_config(page_title="Olett Auditoría Pro", page_icon="🦉", layout="wide")

st.title("🦉 Auditoría de Precisión Olett")
st.markdown("### Validación Triple: RFC, Periodo y Número de Operación")
st.info("Sube el 'Detalle' y el 'Acuse' para realizar el cruce automático.")

# 2. Cargador de archivos
archivos = st.file_uploader("Arrastra aquí tus PDFs del SAT", type="pdf", accept_multiple_files=True)

def extraer_datos_sat(texto):
    """Lógica para limpiar y extraer metadatos de los PDFs"""
    datos = {}
    # Convertimos saltos de línea en espacios para que las búsquedas no fallen
    texto_limpio = texto.replace('\n', ' ')
    
    # --- CRITERIOS DE VALIDACIÓN (Buscamos en ambos tipos de doc) ---
    
    # RFC: Busca el patrón estándar de 12 o 13 caracteres
    rfc_match = re.search(r'[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}', texto_limpio)
    datos['RFC'] = rfc_match.group() if rfc_match else "No encontrado"
    
    # Número de Operación: La llave para unir los archivos
    op_match = re.search(r'NÚMERO DE OPERACIÓN:\s*(\d+)', texto_limpio)
    datos['Operacion'] = op_match.group(1) if op_match else "N/A"
    
    # Periodo: Mes y Año (ej: FEBRERO DE 2026)
    periodo_match = re.search(r'PERIODO:\s*([A-Z\s]+20\d{2})', texto_limpio)
    datos['Periodo'] = periodo_match.group(1).strip() if periodo_match else "N/A"

    # --- DATOS EXCLUSIVOS DEL ACUSE ---
    if "ACUSE DE RECIBO" in texto_limpio:
        datos['Tipo'] = "ACUSE"
        
        # Monto total de la Línea de Captura
        pago_match = re.search(r'TOTAL A PAGAR.*?([\d,]+)', texto_limpio)
        datos['Total_Acuse'] = pago_match.group(1) if pago_match else "0"
        
        # Saldo de IVA (Cantidad a cargo)
        iva_match = re.search(r'VALOR AGREGADO.*?CANTIDAD A CARGO.*?([\d,]+)', texto_limpio)
        datos['IVA_Saldo'] = f"${iva_match.group(1)}" if iva_match else "$0.00"
        
        # Saldo de ISR Retenciones por Salarios
        isr_match = re.search(r'RETENCIONES POR SALARIOS.*?CANTIDAD A CARGO.*?([\d,]+)', texto_limpio)
        datos['ISR_Retenciones'] = f"${isr_match.group(1)}" if isr_match else "$0.00"
    else:
        datos['Tipo'] = "DETALLE"
        
    return datos

# 3. Procesamiento de los archivos subidos
if archivos:
    grupos = {} # Diccionario para agrupar Detalle y Acuse por su número de operación
    
    for arc in archivos:
        with pdfplumber.open(arc) as pdf:
            # Leemos todas las páginas y pasamos a mayúsculas
            texto_full = "".join([p.extract_text().upper() for p in pdf.pages])
            info = extraer_datos_sat(texto_full)
            num_op = info['Operacion']
            
            # Si no existe el grupo para esta operación, lo creamos
            if num_op not in grupos:
                grupos[num_op] = {'DETALLE': None, 'ACUSE': None}
            
            # Guardamos el archivo según sea Detalle o Acuse
            grupos[num_op][info['Tipo']] = info

    # 4. Mostrar Resultados y Validaciones
    for op, docs in grupos.items():
        if op == "N/A": 
            st.error("❌ Se subió un archivo que no tiene Número de Operación visible.")
            continue
        
        st.subheader(f"📑 Revisión Operación: {op}")
        
        detalle = docs['DETALLE']
        acuse = docs['ACUSE']
        
        if detalle and acuse:
            # --- LA TRIPLE VALIDACIÓN CRÍTICA ---
            match_rfc = (detalle['RFC'] == acuse['RFC'])
            match_periodo = (detalle['Periodo'] == acuse['Periodo'])
            
            if match_rfc and match_periodo:
                st.success(f"✅ CONCILIACIÓN EXITOSA: Los documentos corresponden al mismo contribuyente y periodo.")
                
                # Columnas para mostrar resultados limpios (Solo del Acuse)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("IVA (Acuse)", acuse['IVA_Saldo'])
                with col2:
                    st.metric("ISR Retenciones (Acuse)", acuse['ISR_Retenciones'])
                with col3:
                    st.metric("Total a Pagar (Acuse)", f"${acuse['Total_Acuse']}")
                
                st.write(f"**Contribuyente:** {acuse['RFC']} | **Periodo:** {acuse['Periodo']}")
            else:
                st.error("❌ DISCREPANCIA DETECTADA: Los archivos tienen el mismo número de operación pero el RFC o el Periodo NO coinciden.")
                
                # Tabla comparativa para que Yahir vea el error
                error_df = pd.DataFrame({
                    "Dato": ["RFC", "Periodo"],
                    "En Detalle": [detalle['RFC'], detalle['Periodo']],
                    "En Acuse": [acuse['RFC'], acuse['Periodo']]
                })
                st.table(error_df)
        else:
            tipo_falta = "ACUSE" if not acuse else "DETALLE"
            st.warning(f"⚠️ Falta el archivo de **{tipo_falta}** para completar la validación de la operación {op}.")

st.divider()
st.caption("Desarrollado para Despacho Olett - Auditoría Automatizada 2026")