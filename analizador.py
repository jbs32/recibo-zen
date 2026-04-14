import os
from pypdf import PdfReader
import ollama

def extraer_texto_pdf(ruta_archivo):
    try:
        reader = PdfReader(ruta_archivo)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text()
        return texto
    except Exception as e:
        return f"Error al leer el PDF: {e}"

def consultoria_ia(texto_factura):
    print("\n🧠 GestorFácil está 'leyendo' tu factura de Visalia con IA local...")
    
    prompt = f"""
    Eres un asistente experto en energía para personas mayores. 
    Analiza este texto de una factura de la compañía Visalia. 
    Responde en ESPAÑOL de forma muy clara, cariñosa y sencilla:
    1. Importe total a pagar (en euros).
    2. ¿Qué es lo que más está costando? (Potencia, consumo o algún servicio extra).
    3. Un consejo práctico para que esta persona ahorre.
    
    Usa un lenguaje que un abuelo pueda entender perfectamente.
    
    Texto de la factura:
    {texto_factura[:2500]} 
    """
    
    try:
        respuesta = ollama.generate(model='llama3', prompt=prompt)
        print("\n" + "—"*50)
        print("      🌟 TU INFORME DE GESTORFÁCIL")
        print("—"*50)
        print(respuesta['response'])
        print("—"*50)
        print("\n[Privacidad: Tus datos han sido procesados localmente y ya han sido borrados de la sesión.]")
    except Exception as e:
        print(f"Error al conectar con la IA: {e}")

if __name__ == "__main__":
    print("\n--- BIENVENIDO AL PROTOTIPO DE GESTORFÁCIL ---")
    ruta = input("📄 Arrastra tu factura de Visalia aquí y pulsa Enter: ").strip().replace("\\ ", " ")
    
    # Limpiar ruta para Mac si tiene espacios
    if ruta.startswith("'") or ruta.startswith('"'):
        ruta = ruta[1:-1]

    if os.path.exists(ruta):
        texto = extraer_texto_pdf(ruta)
        consultoria_ia(texto)
    else:
        print(f"❌ No encuentro el archivo en: {ruta}")
