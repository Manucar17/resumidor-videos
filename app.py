import os
import tempfile
import time
import streamlit as st
from google import genai

# Configuración de página accesible y limpia
st.set_page_config(page_title="Resumidor de Vídeos", page_icon="🎬", layout="centered")

st.title("🎬 Resumidor de Vídeos y Audio")
st.write("Sube un vídeo o audio y obtén un resumen automático claro y fácil de leer.")

# Cargar la API Key oculta desde la configuración del servidor
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("Error: No se ha configurado la clave API de Gemini.")
    st.stop()

client = genai.Client(api_key=api_key)

# Selector de archivo grande y visible
uploaded_file = st.file_uploader(
    "1. Selecciona tu archivo de vídeo o audio",
    type=["mp4", "mov", "avi", "mkv", "mp3", "m4a", "wav"],
)

if uploaded_file is not None:
    st.info(f"📁 Archivo preparado: **{uploaded_file.name}**")

    if st.button("🚀 Generar Resumen", type="primary", use_container_width=True):
        try:
            with st.spinner(
                "⏳ Analizando el vídeo... Esto puede tardar un par de minutos."
            ):
                # Guardar archivo temporal en el servidor
                file_ext = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=file_ext
                ) as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name

                # Subir vídeo directamente a Gemini (sin usar Whisper local)
                uploaded_media = client.files.upload(file=tmp_path)

                # Esperar a que la API procese el archivo
                while uploaded_media.state.name == "PROCESSING":
                    time.sleep(4)
                    uploaded_media = client.files.get(name=uploaded_media.name)

                if uploaded_media.state.name == "FAILED":
                    raise Exception("Fallo en el procesamiento del vídeo.")

                # Prompt para la IA
                prompt = """
                Analiza el audio/vídeo adjunto y genera un informe claro y estructurado en español:

                # 📌 Resumen General
                Explica de qué trata el vídeo de forma clara y accesible en 2 o 3 párrafos.

                # 💡 Puntos Clave e Ideas Principales
                Lista ordenada con viñetas de las ideas o temas más importantes explicados.

                # 📝 Anotaciones y Detalle
                Resalta decisiones, fechas, nombres, recomendaciones o tareas mencionadas.
                """

                # Generar respuesta con Gemini 2.5 Flash
                response = client.models.generate_content(
                    model="gemini-2.5-flash", contents=[uploaded_media, prompt]
                )

                # Limpieza de archivos en la nube
                client.files.delete(name=uploaded_media.name)
                os.remove(tmp_path)

            st.success("✨ ¡Resumen completado!")
            st.markdown("---")
            st.markdown(response.text)

            # Botón de descarga directa
            st.download_button(
                label="📥 Descargar resumen en un archivo de texto (.txt)",
                data=response.text,
                file_name=f"Resumen_{uploaded_file.name}.txt",
                mime="text/plain",
                use_container_width=True,
            )

        except Exception as e:
            st.error(f"Ocurrió un error al procesar el archivo: {e}")