import os
import tempfile
import time
import streamlit as st
import google.generativeai as genai

# Configuración visual de la aplicación
st.set_page_config(page_title="Resumidor de Videos y Audio", page_icon="🎬")

st.title("🎬 Resumidor de Videos y Audio")
st.write("Sube un vídeo o audio y obtén un resumen automático claro y detallado.")

# Configuración de la clave de API (obtenida de secretos o de variable de entorno)
API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))

if not API_KEY:
    API_KEY = st.sidebar.text_input("Introduce tu Gemini API Key:", type="password")

if API_KEY:
    genai.configure(api_key=API_KEY)


def obtener_ultimo_modelo_flash():
    """Consulta directamente a la API de Google qué modelos están activos

    y selecciona automáticamente el modelo Flash más reciente.
    """
    try:
        modelos = [
            m.name
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
        ]
        # Filtramos los modelos de tipo 'flash'
        modelos_flash = [m for m in modelos if "flash" in m.lower()]

        if modelos_flash:
            # Devuelve el modelo más reciente disponible sin el prefijo 'models/'
            return modelos_flash[0].replace("models/", "")
        return modelos[0].replace("models/", "")
    except Exception as e:
        # Modelo por defecto si hay algún problema de red al listar
        return "gemini-2.5-flash"


# 1. Selector de archivo
archivo = st.file_uploader(
    "1. Selecciona tu archivo de vídeo o audio",
    type=["mp3", "wav", "mp4", "mkv", "mov", "avi"],
)

if archivo:
    st.info(f"📂 Archivo preparado: **{archivo.name}**")

    # Botón principal
    if st.button("🚀 Generar Resumen"):
        if not API_KEY:
            st.error("Por favor, introduce tu API Key para continuar.")
        else:
            # Paso A: Obtener el modelo activo más reciente sin listas fijas
            with st.spinner("Conectando con Google API para detectar el modelo activo..."):
                modelo_activo = obtener_ultimo_modelo_flash()

            st.write(f"⚙️ Procesando con modelo: `{modelo_activo}`")

            try:
                # Paso B: Guardar temporalmente el archivo subido para enviarlo a la API
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=os.path.splitext(archivo.name)[1]
                ) as tmp_file:
                    tmp_file.write(archivo.getvalue())
                    tmp_path = tmp_file.name

                # Paso C: Subir el archivo multimedia a Google Gemini
                with st.spinner("Subiendo archivo multimedia a los servidores de Gemini..."):
                    archivo_gemini = genai.upload_file(path=tmp_path)

                # Esperar a que el archivo termine de procesarse en Google (especialmente para vídeos grandes)
                with st.spinner("Esperando a que Gemini procese el archivo de vídeo/audio..."):
                    while archivo_gemini.state.name == "PROCESSING":
                        time.sleep(2)
                        archivo_gemini = genai.get_file(archivo_gemini.name)

                    if archivo_gemini.state.name == "FAILED":
                        raise ValueError("Google no pudo procesar el archivo multimedia.")

                # Paso D: Generar el resumen con el modelo detectado
                with st.spinner("Generando el resumen automático..."):
                    model = genai.GenerativeModel(model_name=modelo_activo)
                    prompt = (
                        "Haz un resumen detallado, estructurado y claro del contenido "
                        "de este archivo multimedia. Destaca los puntos clave e ideas principales."
                    )
                    respuesta = model.generate_content([archivo_gemini, prompt])

                # Mostrar resultado
                st.success("¡Resumen generado con éxito!")
                st.markdown("---")
                st.write(respuesta.text)

                # Limpieza del archivo subido en la nube y local
                genai.delete_file(archivo_gemini.name)
                os.remove(tmp_path)

            except Exception as e:
                st.error(f"Ocurrió un problema al procesar el archivo: {e}")
