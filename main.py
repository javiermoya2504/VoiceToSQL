import speech_recognition as sr
import whisper
import numpy as np
import tempfile
import os
import torch
import openai
import argparse
import sqlite3

db_path = "identifier.sqlite"

# Leer la clave de API de OpenAI
with open('openai_api_key.txt') as f:
    api_key = f.readline().strip()
openai.api_key = api_key

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

def get_voice_command(timeout):
    r = sr.Recognizer()
    with sr.Microphone(sample_rate=16000) as source:
        r.adjust_for_ambient_noise(source)
        print("Empieza a escuchar...")
        try:
            audio = r.listen(source, timeout)
        except sr.WaitTimeoutError:
            print("Tiempo agotado: No se detectó voz.")
            return
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav.write(audio.get_wav_data())
        result = audio_model.transcribe(temp_wav.name, fp16=torch.cuda.is_available())
        text = result['text'].strip()
        os.remove(temp_wav.name)
        return text

def ask_to_continue():
    while True:
        continuar = input("¿Deseas continuar editando? Ingresa 'y' o 'n': ")
        if continuar == "y":
            return True
        elif continuar == "n":
            return False
        else:
            print("Entrada inválida. Ingresa 'y' o 'n'.")

def ejecutar_sql(sql_query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(sql_query)
        resultados = cursor.fetchall()
        for fila in resultados:
            print(fila)
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
    finally:
        conn.close()

def get_SQL_query(timeout):
    esquema_bd = get_db_schema(db_path)
    messages = [
        {"role": "system", "content": f"Eres un científico de datos que ayuda a escribir consultas SQL. Solo responde con la consulta SQL, sin explicaciones, sin comentarios, y sin formateo markdown como triple backticks. La base de datos tiene la siguiente estructura: \n{esquema_bd}"}
    ]
    while True:
        command = get_voice_command(timeout)
        if not command:
            print("No se detectó ningún comando de voz.")
            continue
        messages.append({"role": "user", "content": command})
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        chat_response = completion.choices[0].message.content
        print(f'ChatGPT: {chat_response}')
        messages.append({"role": "assistant", "content": chat_response})
        continuar = ask_to_continue()
        if not continuar:
            return command, chat_response

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="tiny", help="Modelo a usar",
                        choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--timeout", default=3, type=float, help="Tiempo máximo de escucha")
    args = parser.parse_args()
    model = args.model
    audio_model = whisper.load_model(model)
    mensaje_usuario, sql_query = get_SQL_query(args.timeout)
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

    print(f'Mensaje original del usuario:  {mensaje_usuario}')
    print('Consulta SQL generada: ', sql_query)
    print('Resultados de la consulta: \n')
    ejecutar_sql(sql_query)