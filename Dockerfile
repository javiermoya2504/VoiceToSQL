FROM python:3.11-slim

# Install system dependencies (add build-essential for gcc)
RUN apt-get update && \
    apt-get install -y ffmpeg portaudio19-dev git build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY clientes.db .
COPY identifier.sqlite .
COPY openai_api_key.txt .

CMD ["python", "main.py"]