import os
import tempfile
import time
import google.generativeai as genai
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="Resumidor de Videos y Audio", page_icon="🎬", layout="centered"
)

st.title("🎬 Resumidor de Videos y Audio")
st.write("Sube un vídeo o audio y obtén un resumen automático claro y detallado.")

# Obtener clave API
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    api_key = st.sidebar.text_input("Introduce tu Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)


def obtener_mejor_modelo():
    """Selecciona el modelo multimodal principal activo evitando modelos incompatibles."""
    try:
        modelos_validos = []
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                nombre = m.name.replace("models/", "")
                # Excluir modelos específicos de voz (TTS), imagen pura o pruebas
                if not any(
                    x in nombre.lower()
                    for x in ["tts", "image", "embedding", "realtime"]
                ):
                    modelos_validos.append(nombre)

        # Priorizar modelos flash estándar
        for m in modelos_validos:
            if "flash" in m and "lite" not in m:
                return m

        return modelos_validos[0] if modelos_validos else "gemini-1.5-flash"
    except Exception:
        return "gemini-1.5-flash"


# 1. Selector de archivo
archivo_subido = st.file_uploader(
    "1. Selecciona tu archivo de vídeo o audio",
    type=["mp3", "wav", "mp4", "mkv", "mov", "avi"],
)

if archivo_subido:
    st.info(f"📂 Archivo preparado: **{archivo_subido.name}**")

    if st.button("🚀 Generar Resumen"):
        if not api_key:
            st.error("Por favor, configura tu API Key de Gemini para continuar.")
            st.stop()

        # Seleccionar el mejor modelo activo
        modelo_activo = obtener_mejor_modelo()
        st.write(f"⚙️ Procesando con el modelo: `{modelo_activo}`")

        tmp_path = None
        archivo_gemini = None

        try:
            # 1. Guardar archivo temporalmente
            with st.spinner("Guardando archivo temporal..."):
                extension = os.path.splitext(archivo_subido.name)[1]
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=extension
                ) as tmp:
                    tmp.write(archivo_subido.getvalue())
                    tmp_path = tmp.name

            # 2. Subir archivo a Gemini (UNA SOLA VEZ)
            with st.spinner(
                "Subiendo vídeo a Google (esto puede tardar unos segundos con archivos grandes)..."
            ):
                archivo_gemini = genai.upload_file(path=tmp_path)

            # 3. Esperar el procesamiento en los servidores de Google
            with st.spinner(
                "Esperando a que los servidores de Google procesen el vídeo..."
            ):
                while archivo_gemini.state.name == "PROCESSING":
                    time.sleep(3)
                    archivo_gemini = genai.get_file(archivo_gemini.name)

                if archivo_gemini.state.name == "FAILED":
                    st.error("Google no pudo procesar este archivo multimedia.")
                    st.stop()

            # 4. Generar el resumen
            with st.spinner("Generando el resumen automático..."):
                model = genai.GenerativeModel(modelo_activo)
                prompt = (
                    "Haz un resumen detallado, estructurado y claro del contenido "
                    "de este archivo. Destaca los puntos clave, temas principales y conclusiones."
                )
                respuesta = model.generate_content([archivo_gemini, prompt])

            # Mostrar resultado
            st.success("¡Resumen generado con éxito!")
            st.markdown("---")
            st.write(respuesta.text)

        except Exception as e:
            # Muestra el error exacto si ocurre algún fallo con la API Key, cuota o archivo
            st.error(f"❌ Error durante el proceso: {e}")

        finally:
            # Limpieza de archivos
            if archivo_gemini:
                try:
                    genai.delete_file(archivo_gemini.name)
                except Exception:
                    pass
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
