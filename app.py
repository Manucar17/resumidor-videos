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


def obtener_modelos_activos():
    """Consulta en tiempo real a Google qué modelos existen y están activos.

    Evita poner modelos antiguos a fuego en el código.
    """
    try:
        modelos = []
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                # Quitamos el prefijo 'models/'
                nombre = m.name.replace("models/", "")
                modelos.append(nombre)

        # Filtramos preferiblemente los modelos 'flash'
        modelos_flash = [m for m in modelos if "flash" in m.lower()]

        if modelos_flash:
            return modelos_flash
        return modelos if modelos else ["gemini-1.5-flash"]
    except Exception:
        # Fallback de seguridad
        return ["gemini-1.5-flash"]


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

        # Obtenemos automáticamente los modelos que Google tiene activos HOY
        modelos_disponibles = obtener_modelos_activos()
        exito = False

        for modelo in modelos_disponibles:
            st.write(f"⚙️ Procesando con modelo: `{modelo}`")

            try:
                # Guardar archivo temporalmente
                extension = os.path.splitext(archivo_subido.name)[1]
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=extension
                ) as tmp:
                    tmp.write(archivo_subido.getvalue())
                    tmp_path = tmp.name

                # Subida a Gemini
                with st.spinner("Subiendo archivo a los servidores de Google..."):
                    archivo_gemini = genai.upload_file(path=tmp_path)

                # Procesamiento multimedia en Google
                with st.spinner(
                    "Esperando el procesamiento del archivo multimedia..."
                ):
                    while archivo_gemini.state.name == "PROCESSING":
                        time.sleep(2)
                        archivo_gemini = genai.get_file(archivo_gemini.name)

                    if archivo_gemini.state.name == "FAILED":
                        raise ValueError(
                            "Google no pudo procesar este archivo multimedia."
                        )

                # Generación del resumen
                with st.spinner("Generando el resumen automático..."):
                    model = genai.GenerativeModel(modelo)
                    prompt = (
                        "Haz un resumen detallado, estructurado y claro del contenido "
                        "de este archivo. Destaca los puntos clave, temas principales y conclusiones."
                    )
                    respuesta = model.generate_content([archivo_gemini, prompt])

                # Mostrar resultado
                st.success("¡Resumen generado con éxito!")
                st.markdown("---")
                st.write(respuesta.text)

                # Limpieza de archivos temporales
                try:
                    genai.delete_file(archivo_gemini.name)
                    os.remove(tmp_path)
                except Exception:
                    pass

                exito = True
                break  # Si un modelo funciona, salimos del bucle

            except Exception as e:
                st.warning(
                    f"El modelo `{modelo}` no respondió. Probando alternativa..."
                )

        if not exito:
            st.error(
                "Ocurrió un problema al procesar el archivo con los modelos disponibles."
            )
