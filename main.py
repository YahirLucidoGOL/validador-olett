import pdfplumber
import re

archivo = "prueba.pdf" 

def validador_olett():
    print(f"\n🔎 Analizando documento: {archivo}...")
    
    try:
        with pdfplumber.open(archivo) as pdf:
            # Extraemos todo el texto y lo ponemos en MAYÚSCULAS para no fallar
            texto_completo = ""
            for pagina in pdf.pages:
                texto_completo += pagina.extract_text().upper()
            
            # 1. Buscamos el RFC
            rfc_pattern = r'[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}'
            rfc_encontrado = re.search(rfc_pattern, texto_completo)
            
            # 2. Lógica flexible para el resultado
            # Buscamos "POSITIV" o "NEGATIV" para cubrir ambos géneros (A/O)
            resultado = "DESCONOCIDO"
            if "POSITIV" in texto_completo:
                resultado = "✅ POSITIVA"
            elif "NEGATIV" in texto_completo:
                resultado = "❌ NEGATIVA"

            # 3. Formato de salida profesional
            print("="*40)
            print(f"RESUMEN DE VALIDACIÓN - OLETT")
            print("="*40)
            
            rfc_texto = rfc_encontrado.group() if rfc_encontrado else "NO DETECTADO"
            print(f"CONTRIBUYENTE (RFC): {rfc_texto}")
            print(f"ESTADO FISCAL:      {resultado}")
            print("="*40)

            if "NEGATIVA" in resultado:
                print("\n⚠️  ALERTA: Se detectaron inconsistencias en el SAT.")
                
    except Exception as e:
        print(f"Hubo un error: {e}")

if __name__ == "__main__":
    validador_olett()