FROM python:3.11-slim

# System libraries required by faster-whisper (ctranslate2) and audio conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (separate layer for better cache reuse)
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt

# Copy all source files
COPY . .

# Pre-create runtime directories so the app never errors on first boot
RUN mkdir -p user_data/chroma_db user_data/profiles user_data/logs

# Hugging Face Spaces requires port 7860
EXPOSE 7860
ENV PORT=7860

CMD ["python", "app.py"]
