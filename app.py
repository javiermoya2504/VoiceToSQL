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

# Configuracion de la pagina
st.set_page_config(
    page_title="Voice to SQL",
    page_icon="V",
    layout="wide"
)

# --- CSS personalizado ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Tipografia general */
    html, body, [class*="st-"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    /* Header */
    .app-header {
        background: #2c3e50;
        padding: 2rem 2.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .app-header h1 {
        font-size: 2rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .app-header p {
        color: #bdc3c7;
        font-size: 1rem;
        margin: 0.35rem 0 0 0;
        font-weight: 400;
    }

    /* Label de seccion */
    .section-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: #7f8c8d;
        margin-bottom: 0.75rem;
    }

    /* Seccion de resultados */
    .results-container {
        background: #f7f9fa;
        border: 1px solid #dce1e5;
        border-left: 3px solid #2c3e50;
        border-radius: 6px;
        padding: 1.5rem;
        margin-top: 1rem;
    }

    /* SQL destacado */
    .sql-display {
        background: #2c3e50;
        color: #ecf0f1;
        border-radius: 6px;
        padding: 1.2rem 1.5rem;
        font-family: 'Fira Code', 'Courier New', monospace;
        font-size: 0.9rem;
        margin: 0.75rem 0;
        overflow-x: auto;
        border-left: 3px solid #3498db;
    }

    /* Botones primarios */
    .stButton > button[kind="primary"] {
        background-color: #2c3e50;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        letter-spacing: 0.3px;
        padding: 0.6rem 1.5rem;
        transition: background-color 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #34495e;
    }

    /* Botones secundarios */
    .stButton > button[kind="secondary"] {
        border: 2px solid #2c3e50;
        color: #2c3e50;
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s ease;
        background: transparent;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #2c3e50;
        color: white;
    }

    /* Text area */
    .stTextArea textarea {
        border-radius: 6px;
        border: 1.5px solid #dce1e5;
        font-size: 0.95rem;
        padding: 0.85rem;
        transition: border-color 0.2s ease;
    }
    .stTextArea textarea:focus {
        border-color: #3498db;
        box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.12);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f7f9fa;
    }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        font-size: 1.1rem;
        color: #2c3e50;
        font-weight: 700;
    }

    /* Sidebar pasos */
    .sidebar-step {
        display: flex;
        align-items: flex-start;
        gap: 0.6rem;
        margin-bottom: 0.75rem;
    }
    .step-number {
        background: #2c3e50;
        color: white;
        font-weight: 700;
        font-size: 0.75rem;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        margin-top: 2px;
    }
    .step-text {
        color: #555;
        font-size: 0.88rem;
        line-height: 1.5;
    }

    /* Divider */
    .section-divider {
        border: none;
        height: 1px;
        background: #dce1e5;
        margin: 1.75rem 0;
    }

    /* Ajuste dataframe */
    .stDataFrame {
        border-radius: 6px;
        overflow: hidden;
        border: 1px solid #dce1e5;
    }

    /* Download button */
    .stDownloadButton > button {
        background-color: #27ae60;
        border: none;
        color: white;
        border-radius: 6px;
        font-weight: 600;
        transition: background-color 0.2s ease;
    }
    .stDownloadButton > button:hover {
        background-color: #219a52;
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-success {
        background: #eafaf1;
        color: #27ae60;
        border: 1px solid #c8e6d5;
    }

    /* Spinner color */
    .stSpinner > div > div {
        border-top-color: #3498db !important;
    }
</style>
""", unsafe_allow_html=True)

# Configurar OpenAI
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    st.error("OPENAI_API_KEY no encontrada. Asegurate de tener un archivo .env con OPENAI_API_KEY=tu_clave")
    st.stop()
openai.api_key = api_key

# Path a la base de datos
db_path = "identifier.sqlite"

# Funcion para cargar el modelo Whisper bajo demanda
def get_audio_model():
    if 'audio_model' not in st.session_state:
        with st.spinner('Cargando modelo Whisper (solo la primera vez)...'):
            st.session_state.audio_model = whisper.load_model("tiny")
    return st.session_state.audio_model

# Funcion para obtener el esquema de la BD
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

# Funcion para grabar voz
def grabar_voz():
    audio_model = get_audio_model()

    r = sr.Recognizer()
    try:
        with sr.Microphone(sample_rate=16000) as source:
            st.info("Escuchando... Habla ahora")
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

# Funcion para generar SQL
def generar_sql(texto_usuario):
    esquema_bd = get_db_schema(db_path)
    messages = [
        {"role": "system", "content": f"Eres un cientifico de datos que ayuda a escribir consultas SQL. Solo responde con la consulta SQL, sin explicaciones, sin comentarios, y sin formateo markdown como triple backticks. La base de datos tiene la siguiente estructura: \n{esquema_bd}"},
        {"role": "user", "content": texto_usuario}
    ]

    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    sql_query = completion.choices[0].message.content
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
    return sql_query

# Funcion para ejecutar SQL
def ejecutar_sql(sql_query):
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(sql_query, conn)
        return df, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()

# Funcion para generar PDF
def generar_pdf(consulta_usuario, sql_query, df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elementos = []

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=30,
        alignment=1
    )

    subtitulo_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12
    )

    titulo = Paragraph("Reporte de Consulta SQL", titulo_style)
    elementos.append(titulo)
    elementos.append(Spacer(1, 0.3*inch))

    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info = Paragraph(f"<b>Fecha de generacion:</b> {fecha_actual}", styles['Normal'])
    elementos.append(info)
    elementos.append(Spacer(1, 0.2*inch))

    subtitulo1 = Paragraph("Consulta del Usuario", subtitulo_style)
    elementos.append(subtitulo1)
    consulta_texto = Paragraph(f"<i>{consulta_usuario}</i>", styles['Normal'])
    elementos.append(consulta_texto)
    elementos.append(Spacer(1, 0.2*inch))

    subtitulo2 = Paragraph("Consulta SQL Generada", subtitulo_style)
    elementos.append(subtitulo2)
    sql_texto = Paragraph(f"<font name='Courier'>{sql_query}</font>", styles['Code'])
    elementos.append(sql_texto)
    elementos.append(Spacer(1, 0.3*inch))

    subtitulo3 = Paragraph("Resultados", subtitulo_style)
    elementos.append(subtitulo3)

    if len(df) == 0:
        elementos.append(Paragraph("No se encontraron resultados", styles['Normal']))
    else:
        datos = [df.columns.tolist()] + df.values.tolist()

        if len(datos) > 51:
            datos = datos[:51]
            elementos.append(Paragraph(f"<i>Mostrando las primeras 50 filas de {len(df)} totales</i>", styles['Normal']))
            elementos.append(Spacer(1, 0.1*inch))

        datos_procesados = []
        for fila in datos:
            fila_procesada = []
            for valor in fila:
                valor_str = str(valor)
                if len(valor_str) > 50:
                    valor_str = valor_str[:47] + "..."
                fila_procesada.append(valor_str)
            datos_procesados.append(fila_procesada)

        tabla = Table(datos_procesados)

        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
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

    doc.build(elementos)
    buffer.seek(0)
    return buffer


# =====================
# INTERFAZ PRINCIPAL
# =====================

# Header
st.markdown("""
<div class="app-header">
    <h1>Voice to SQL</h1>
    <p>Consulta tu base de datos usando lenguaje natural, por voz o texto.</p>
</div>
""", unsafe_allow_html=True)

# --- Zona de entrada ---
st.markdown('<p class="section-label">Entrada de consulta</p>', unsafe_allow_html=True)

input_col, btn_col = st.columns([5, 1])

with input_col:
    query_text = st.text_area(
        "Consulta en lenguaje natural",
        value=st.session_state.get('query_text', ''),
        height=100,
        placeholder="Ej: Muestra los 10 clientes con mayor facturacion del ultimo trimestre",
        label_visibility="collapsed"
    )
    if query_text:
        st.session_state.query_text = query_text

with btn_col:
    if st.button("Grabar Voz", use_container_width=True, type="secondary"):
        texto = grabar_voz()
        if texto:
            st.session_state.query_text = texto
            st.rerun()

# Boton principal de ejecucion
if st.button("Ejecutar Consulta", use_container_width=True, type="primary"):
    if 'query_text' in st.session_state and st.session_state.query_text:
        with st.spinner('Generando consulta SQL...'):
            sql_query = generar_sql(st.session_state.query_text)
            st.session_state.sql_query = sql_query

        # Mostrar SQL generado en contenedor destacado
        st.markdown('<p class="section-label">Consulta SQL generada</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="sql-display">{sql_query}</div>', unsafe_allow_html=True)

        with st.spinner('Ejecutando consulta...'):
            df, error = ejecutar_sql(sql_query)

        if error:
            st.error(f"Error al ejecutar la consulta: {error}")
            st.session_state.df_resultados = None
        else:
            st.session_state.df_resultados = df

            # Contenedor de resultados
            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            st.markdown('<p class="section-label">Resultados</p>', unsafe_allow_html=True)
            st.markdown('<div class="results-container">', unsafe_allow_html=True)

            if len(df) == 0:
                st.info("No se encontraron resultados para esta consulta.")
            else:
                st.markdown(f'<span class="status-badge badge-success">{len(df)} filas encontradas</span>', unsafe_allow_html=True)
                st.dataframe(df, use_container_width=True)

            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("Por favor, ingresa una consulta usando voz o texto antes de ejecutar.")

# Boton de PDF integrado en la seccion de resultados
if 'df_resultados' in st.session_state and st.session_state.df_resultados is not None:
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    with st.spinner('Generando PDF...'):
        pdf_buffer = generar_pdf(
            st.session_state.query_text,
            st.session_state.sql_query,
            st.session_state.df_resultados
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"reporte_sql_{timestamp}.pdf"

    dl_col1, dl_col2, dl_col3 = st.columns([2, 1, 2])
    with dl_col2:
        st.download_button(
            label="Descargar PDF",
            data=pdf_buffer,
            file_name=nombre_archivo,
            mime="application/pdf",
            use_container_width=True
        )

# --- Sidebar ---
with st.sidebar:
    st.markdown("## Informacion")
    st.markdown("""
<div style="margin-top: 0.5rem;">
    <div class="sidebar-step">
        <div class="step-number">1</div>
        <div class="step-text">Escribe tu consulta en lenguaje natural o presiona <b>Grabar Voz</b>.</div>
    </div>
    <div class="sidebar-step">
        <div class="step-number">2</div>
        <div class="step-text">Presiona <b>Ejecutar Consulta</b> para generar el SQL automaticamente.</div>
    </div>
    <div class="sidebar-step">
        <div class="step-number">3</div>
        <div class="step-text">Revisa los resultados y descarga el reporte en PDF si lo necesitas.</div>
    </div>
</div>
""", unsafe_allow_html=True)

    with st.expander("Esquema de la base de datos"):
        try:
            schema = get_db_schema(db_path)
            st.code(schema, language=None)
        except Exception:
            st.warning("No se pudo cargar el esquema de la base de datos.")
