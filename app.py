import streamlit as st
import speech_recognition as sr
import whisper
import tempfile
import os
import torch
import openai
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Cargar variables de entorno
load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="Voice to SQL",
    page_icon="🎤",
    layout="wide"
)

# Configurar OpenAI
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    st.error("OPENAI_API_KEY no encontrada. Asegúrate de tener un archivo .env con OPENAI_API_KEY=tu_clave")
    st.stop()
openai.api_key = api_key

# Path a la base de datos
db_path = "identifier.sqlite"

# Función para cargar el modelo Whisper bajo demanda
def get_audio_model():
    if 'audio_model' not in st.session_state:
        with st.spinner('Cargando modelo Whisper (solo la primera vez)...'):
            st.session_state.audio_model = whisper.load_model("tiny")
    return st.session_state.audio_model

# Función para obtener el esquema de la BD
def get_db_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    schema = ""
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns]
        schema += f"Tabla: {table_name}\nColumnas: {', '.join(col_names)}\n"
    conn.close()
    return schema

# Función para grabar voz
def grabar_voz():
    # Cargar modelo solo cuando se necesita
    audio_model = get_audio_model()

    r = sr.Recognizer()
    try:
        with sr.Microphone(sample_rate=16000) as source:
            st.info("🎤 Escuchando... Habla ahora")
            r.adjust_for_ambient_noise(source, duration=1)
            audio = r.listen(source, timeout=5, phrase_time_limit=10)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav.write(audio.get_wav_data())
            temp_path = temp_wav.name

        result = audio_model.transcribe(temp_path, fp16=torch.cuda.is_available())
        text = result['text'].strip()
        os.remove(temp_path)
        return text
    except Exception as e:
        st.error(f"Error al grabar: {str(e)}")
        return None

# Función para generar SQL
def generar_sql(texto_usuario):
    esquema_bd = get_db_schema(db_path)
    messages = [
        {"role": "system", "content": f"Eres un científico de datos que ayuda a escribir consultas SQL. Solo responde con la consulta SQL, sin explicaciones, sin comentarios, y sin formateo markdown como triple backticks. La base de datos tiene la siguiente estructura: \n{esquema_bd}"},
        {"role": "user", "content": texto_usuario}
    ]

    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    sql_query = completion.choices[0].message.content
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
    return sql_query

# Función para ejecutar SQL
def ejecutar_sql(sql_query):
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(sql_query, conn)
        return df, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()

# Función para generar PDF
def generar_pdf(consulta_usuario, sql_query, df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elementos = []

    # Estilos
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=1  # Centrado
    )

    subtitulo_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12
    )

    # Título del reporte
    titulo = Paragraph("Reporte de Consulta SQL", titulo_style)
    elementos.append(titulo)
    elementos.append(Spacer(1, 0.3*inch))

    # Información de la consulta
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info = Paragraph(f"<b>Fecha de generación:</b> {fecha_actual}", styles['Normal'])
    elementos.append(info)
    elementos.append(Spacer(1, 0.2*inch))

    # Consulta del usuario
    subtitulo1 = Paragraph("Consulta del Usuario", subtitulo_style)
    elementos.append(subtitulo1)
    consulta_texto = Paragraph(f"<i>{consulta_usuario}</i>", styles['Normal'])
    elementos.append(consulta_texto)
    elementos.append(Spacer(1, 0.2*inch))

    # Consulta SQL generada
    subtitulo2 = Paragraph("Consulta SQL Generada", subtitulo_style)
    elementos.append(subtitulo2)
    sql_texto = Paragraph(f"<font name='Courier'>{sql_query}</font>", styles['Code'])
    elementos.append(sql_texto)
    elementos.append(Spacer(1, 0.3*inch))

    # Resultados
    subtitulo3 = Paragraph("Resultados", subtitulo_style)
    elementos.append(subtitulo3)

    if len(df) == 0:
        elementos.append(Paragraph("No se encontraron resultados", styles['Normal']))
    else:
        # Preparar datos para la tabla
        datos = [df.columns.tolist()] + df.values.tolist()

        # Limitar a primeras 50 filas para PDFs grandes
        if len(datos) > 51:  # 1 header + 50 filas
            datos = datos[:51]
            elementos.append(Paragraph(f"<i>Mostrando las primeras 50 filas de {len(df)} totales</i>", styles['Normal']))
            elementos.append(Spacer(1, 0.1*inch))

        # Convertir valores a strings y limitar longitud
        datos_procesados = []
        for fila in datos:
            fila_procesada = []
            for valor in fila:
                valor_str = str(valor)
                # Limitar longitud de cada celda
                if len(valor_str) > 50:
                    valor_str = valor_str[:47] + "..."
                fila_procesada.append(valor_str)
            datos_procesados.append(fila_procesada)

        # Crear tabla
        tabla = Table(datos_procesados)

        # Estilo de la tabla
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
        ]))

        elementos.append(tabla)
        elementos.append(Spacer(1, 0.2*inch))
        elementos.append(Paragraph(f"<b>Total de filas:</b> {len(df)}", styles['Normal']))

    # Construir PDF
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# Interfaz principal
st.title("🎤 Voice to SQL")
st.markdown("Consulta tu base de datos usando voz o texto")

# Crear dos columnas
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("Opciones de entrada")

    # Botón para grabar voz
    if st.button("🎤 Grabar Voz", use_container_width=True, type="primary"):
        texto = grabar_voz()
        if texto:
            st.session_state.query_text = texto

with col2:
    st.subheader("Consulta")

    # Caja de texto
    query_text = st.text_area(
        "O escribe tu consulta aquí:",
        value=st.session_state.get('query_text', ''),
        height=100,
        placeholder="Ejemplo: Muéstrame todos los usuarios registrados el último mes"
    )

    if query_text:
        st.session_state.query_text = query_text

# Botón para ejecutar consulta
if st.button("▶️ Ejecutar Consulta", use_container_width=True):
    if 'query_text' in st.session_state and st.session_state.query_text:
        with st.spinner('Generando consulta SQL...'):
            sql_query = generar_sql(st.session_state.query_text)
            st.session_state.sql_query = sql_query

        st.success("✅ Consulta SQL generada")
        st.code(sql_query, language="sql")

        with st.spinner('Ejecutando consulta...'):
            df, error = ejecutar_sql(sql_query)

        if error:
            st.error(f"❌ Error al ejecutar la consulta: {error}")
            st.session_state.df_resultados = None
        else:
            # Guardar resultados en session_state para el PDF
            st.session_state.df_resultados = df

            st.subheader("📊 Resultados")
            if len(df) == 0:
                st.info("No se encontraron resultados")
            else:
                st.dataframe(df, use_container_width=True)
                st.caption(f"Total de filas: {len(df)}")
    else:
        st.warning("⚠️ Por favor, ingresa una consulta usando voz o texto")

# Botón para descargar PDF (solo se muestra si hay resultados)
if 'df_resultados' in st.session_state and st.session_state.df_resultados is not None:
    st.markdown("---")
    col_pdf1, col_pdf2, col_pdf3 = st.columns([1, 2, 1])
    with col_pdf2:
        if st.button("📄 Descargar Reporte en PDF", use_container_width=True, type="secondary"):
            with st.spinner('Generando PDF...'):
                pdf_buffer = generar_pdf(
                    st.session_state.query_text,
                    st.session_state.sql_query,
                    st.session_state.df_resultados
                )

                # Nombre del archivo con timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_archivo = f"reporte_sql_{timestamp}.pdf"

                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=pdf_buffer,
                    file_name=nombre_archivo,
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("✅ PDF generado correctamente")

# Sidebar con información
with st.sidebar:
    st.header("ℹ️ Información")
    st.markdown("""
    ### Cómo usar:
    1. **Opción 1:** Presiona el botón "Grabar Voz" y habla tu consulta
    2. **Opción 2:** Escribe tu consulta en la caja de texto
    3. Presiona "Ejecutar Consulta" para ver los resultados

    ### Esquema de la BD:
    """)
    try:
        schema = get_db_schema(db_path)
        st.text(schema)
    except:
        st.warning("No se pudo cargar el esquema de la base de datos")