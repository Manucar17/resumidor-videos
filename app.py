import os
import tempfile
import time
import streamlit as st
from google import genai

# Configuración de interfaz accesibles y limpia
st.set_page_config(page_title="Resumidor de Vídeos", page_icon="🎬", layout="centered")

st.title("🎬 Resumidor de Vídeos y Audio")
st.write("Sube un vídeo o audio y obtén un resumen automático claro y detallado.")

# Cargar la API Key desde los Secrets de Streamlit
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("Error: No se ha configurado la clave API de Gemini en Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

def get_flash_models(client_instance):
    """
    Busca dinámicamente:
    1. Modelos 'Flash' con capacidad de pensamiento/razonamiento extendido ('thinking' / 'extended').
    2. Modelos 'Flash' estándar como respaldo seguro.
    """
    try:
        all_models = list(client_instance.models.list(config={"query_base": True}))
        
        exclude_keywords = ["image", "imagen", "nano", "embed", "tts", "stt", "realtime", "audio-only"]
        
        flash_thinking = []
        flash_standard = []
        
        for m in all_models:
            name = m.name.replace("models/", "").lower()
            if name.startswith("gemini-") and not any(k in name for k in exclude_keywords):
                if "flash" in name:
                    if any(term in name for term in ["thinking", "extended", "reasoning", "exp"]):
                        flash_thinking.append(name)
                    else:
                        flash_standard.append(name)
                        
        flash_thinking.sort()
        flash_standard.sort()
        
        # Seleccionar el mejor modelo Flash Thinking/Extended si existe, y el mejor Flash estándar de respaldo
        preferred_model = flash_thinking[-1] if flash_thinking else (flash_standard[-1] if flash_standard else "gemini-2.5-flash")
        fallback_model = flash_standard[-1] if flash_standard else "gemini-2.5-flash"
        
        return preferred_model, fallback_model
    except Exception:
        # En caso de error de red consultando la lista, usar valores por defecto super estables
        return "gemini-2.5-flash", "gemini-2.5-flash"


uploaded_file = st.file_uploader(
    "1. Selecciona tu archivo de vídeo o audio",
    type=["mp4", "mov", "avi", "mkv", "mp3", "m4a", "wav"],
)

if uploaded_file is not None:
    st.info(f"📁 Archivo preparado: **{uploaded_file.name}**")

    if st.button("🚀 Generar Resumen", type="primary", use_container_width=True):
        try:
            primary_model, backup_model = get_flash_models(client)
            
            with st.spinner("⏳ Analizando el contenido... Esto puede tardar un par de minutos."):
                # Guardar archivo temporalmente
                file_ext = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name

                # Subir vídeo a la API
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

                # Intento 1: Usar Flash Extended / Thinking
                try:
                    st.caption(f"🤖 Usando modelo: `{primary_model}`")
                    response = client.models.generate_content(
                        model=primary_model, 
                        contents=[uploaded_media, prompt]
                    )
                except Exception as e:
                    # Intento 2: Si por alguna razón el modelo extended no responde, salta al Flash estándar sin fallar
                    st.warning("⚠️ Ajustando automáticamente al modelo rápido de respaldo...")
                    st.caption(f"🤖 Usando modelo de respaldo: `{backup_model}`")
                    response = client.models.generate_content(
                        model=backup_model, 
                        contents=[uploaded_media, prompt]
                    )

                # Limpieza de archivos temporales
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
