import os
import tempfile
import time
import streamlit as st
from google import genai

# Configuración limpia e intuitiva
st.set_page_config(page_title="Resumidor de Vídeos", page_icon="🎬", layout="centered")

st.title("🎬 Resumidor de Vídeos y Audio")
st.write("Sube un vídeo o audio y obtén un resumen automático claro y detallado.")

# Cargar la API Key desde los Secrets
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("Error: No se ha configurado la clave API de Gemini en Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# Lista priorizada de modelos oficiales estándar con cuota gratuita para vídeo
MODEL_PRIORITY = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

uploaded_file = st.file_uploader(
    "1. Selecciona tu archivo de vídeo o audio",
    type=["mp4", "mov", "avi", "mkv", "mp3", "m4a", "wav"],
)

if uploaded_file is not None:
    st.info(f"📁 Archivo preparado: **{uploaded_file.name}**")

    if st.button("🚀 Generar Resumen", type="primary", use_container_width=True):
        try:
            with st.spinner("⏳ Analizando el contenido... Esto puede tardar un par de minutos."):
                file_ext = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name

                # Subida de archivo a la API de Google
                uploaded_media = client.files.upload(file=tmp_path)

                while uploaded_media.state.name == "PROCESSING":
                    time.sleep(4)
                    uploaded_media = client.files.get(name=uploaded_media.name)

                if uploaded_media.state.name == "FAILED":
                    raise Exception("Fallo en el procesamiento del vídeo.")

                prompt = """
                Analiza el contenido audiovisual adjunto y genera un informe estructurado, detallado y claro en español:

                # 📌 Resumen General
                Explicación clara y comprensible del tema principal del vídeo en 2 o 3 párrafos.

                # 💡 Puntos Clave
                Listado ordenado con las ideas, explicaciones y conceptos más importantes.

                # 📝 Anotaciones y Detalles
                Fechas, nombres, decisiones tomadas, datos cuantitativos o tareas mencionadas en el vídeo.
                """

                response = None
                last_error = None

                # Probar secuencialmente los modelos estándar de la lista
                for model_name in MODEL_PRIORITY:
                    try:
                        st.caption(f"🤖 Procesando con modelo: `{model_name}`")
                        response = client.models.generate_content(
                            model=model_name, 
                            contents=[uploaded_media, prompt]
                        )
                        if response:
                            break
                    except Exception as e:
                        last_error = e
                        st.warning(f"⚠️ El modelo `{model_name}` no respondió. Probando alternativa...")
                        continue

                if not response:
                    raise last_error

                # Limpieza de archivos en el servidor
                client.files.delete(name=uploaded_media.name)
                os.remove(tmp_path)

            st.success("✨ ¡Resumen completado con éxito!")
            st.markdown("---")
            st.markdown(response.text)

            st.download_button(
                label="📥 Descargar resumen en un archivo de texto (.txt)",
                data=response.text,
                file_name=f"Resumen_{uploaded_file.name}.txt",
                mime="text/plain",
                use_container_width=True,
            )

        except Exception as e:
            st.error(f"Ocurrió un problema al procesar el archivo: {e}")
