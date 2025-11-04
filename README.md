# 🎙️ Voice-to-SQL: Consultas por voz con IA y SQLite

Este proyecto permite ejecutar consultas SQL en una base de datos SQLite usando comandos de voz. Utiliza reconocimiento de voz con Whisper, procesamiento natural de lenguaje con OpenAI y una base de datos local para generar y ejecutar consultas automáticamente.

---

## 🚀 ¿Qué hace?

1. Escucha un comando de voz del usuario (por ejemplo: "Dame la tabla clientes").
2. Transcribe el audio usando Whisper.
3. Genera la consulta SQL con OpenAI (ejemplo: `SELECT * FROM clientes;`).
4. Ejecuta la consulta en una base de datos SQLite.
5. Imprime el mensaje original, la consulta generada y los resultados en consola.

---

## 🧠 Tecnologías utilizadas

- [OpenAI GPT-3.5](https://platform.openai.com/docs) para generar consultas SQL a partir del lenguaje natural.
- [Whisper](https://github.com/openai/whisper) para transcripción automática de voz.
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) y [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) para capturar audio.
- [SQLite3](https://www.sqlite.org/index.html) como base de datos local.

---

## 🧰 Instalación MacOS

### 1. Clona el repositorio:

```bash
git clone https://github.com/tu-usuario/voice-to-sql.git
cd voice-to-sql
```

### 2. Instala las dependencias (macOS):
```bash
brew install portaudio
pip install pyaudio
pip install -r requirements.txt
brew install ffmpeg
```

### 3. Configura tu API key de OpenAI:

Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:
```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. Ejecuta el script con:

```bash
python main.py
```

## 🧰 Instalación Windows

### 1. Clona el repositorio:

```bash
git clone https://github.com/tu-usuario/voice-to-sql.git
cd voice-to-sql
```

### 2. Instala las dependencias:
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configura tu API key de OpenAI:

Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:
```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. Ejecuta el script con:

```bash
python main.py
```

## 🧰 Instalación en Linux con Docker

### 1. Clona el repositorio:

```bash
git clone https://github.com/tu-usuario/voice-to-sql.git
cd voice-to-sql
```

### 2. Configura tu API key de OpenAI:

Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:
```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Construye la imagen:
```bash
docker build -t voicetosql .
```

### 4. Ejecuta el contenedor:
```bash
docker run --rm -it --device /dev/snd voicetosql

```
