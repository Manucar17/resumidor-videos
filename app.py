import os
import tempfile
import time
import streamlit as st
from google import genai

# Configuración de página accesible y limpia
st.set_page_config(page_title="Resumidor de Vídeos", page_icon="🎬", layout="centered")

st.title("🎬 Resumidor de Vídeos y Audio")
st.write(
    "Sube un vídeo o audio y obtén un resumen automático profundo y claro."
)

# Cargar la API Key oculta desde los Secrets del servidor
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("Error: No se ha configurado la clave API de Gemini en Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)


def get_latest_reasoning_model(client_instance):
    """Consulta a la API de Google y obtiene dinámicamente el modelo Pro

    (pensamiento extendido) más reciente disponible en tu cuenta.
    """
    try:
        # Obtener el catálogo actualizado de modelos base desde la API
        all_models = list(
            client_instance.models.list(config={"query_base": True})
        )

        # Filtrar modelos de la serie 'pro' (modelos con razonamiento extendido)
        pro_models = []
        for m in all_models:
            model_id = m.name.replace("models/", "")
            if "pro" in model_id.lower() and "embed" not in model_id.lower():
                pro_models.append(model_id)

        if pro_models:
            # Ordenar para tomar la versión/variante más reciente disponible
            pro_models.sort()
            return pro_models[-1]
    except Exception:
        pass

    # Respaldo de seguridad si falla la consulta del catálogo
    return "gemini-2.5-pro"


# Selector de archivo grande y visible
uploaded_file = st.file_uploader(
    "1. Selecciona tu archivo de vídeo o audio",
    type=["mp4", "mov", "avi", "mkv", "mp3", "m4a", "wav"],
)

if uploaded_file is not None:
    st.info(f"📁 Archivo preparado: **{uploaded_file.name}**")

    if st.button("🚀 Generar Resumen", type="primary", use_container_width=True):
        try:
            # Seleccionar dinámicamente el modelo Pro más reciente
            active_model = get_latest_reasoning_model(client)
            st.caption(
                f"🤖 Modelo de pensamiento utilizado: `{active_model}`"
            )

            with st.spinner(
                "⏳ Analizando el vídeo con pensamiento extendido... Esto puede tardar un par de minutos."
            ):
                # Guardar archivo temporal en el servidor
                file_ext = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=file_ext
                ) as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name

                # Subir vídeo directamente a la API de Gemini
                uploaded_media = client.files.upload(file=tmp_path)

                # Esperar a que la API procese el vídeo
                while uploaded_media.state.name == "PROCESSING":
                    time.sleep(4)
                    uploaded_media = client.files.get(name=uploaded_media.name)

                if uploaded_media.state.name == "FAILED":
                    raise Exception("Fallo en el procesamiento del vídeo.")

                # Prompt estructurado para análisis profundo
                prompt = """
                Analiza en profundidad el contenido audiovisual adjunto utilizando tu capacidad de razonamiento extendido y genera un informe detallado en español:

                # 📌 Resumen General
                Proporciona una explicación detallada del tema central y contexto del vídeo en 2 o 3 párrafos.

                # 💡 Puntos Clave y Razonamiento
                Desglosa los argumentos, conceptos principales y explicaciones clave presentadas en el material.

                # 📝 Anotaciones, Decisiones y Detalles
                Extrae fechas, nombres propios, decisiones tomadas, datos cuantitativos o tareas mencionadas.
                """

                # Generar contenido usando el modelo Pro detectado
                response = client.models.generate_content(
                    model=active_model, contents=[uploaded_media, prompt]
                )

                # Limpieza de archivos temporales en la nube
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
