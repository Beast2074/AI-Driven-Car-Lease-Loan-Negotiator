FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (Tesseract OCR for scanned PDF extraction)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files (backend, frontend, configs)
COPY . .

ENV PYTHONPATH="."
ENV PYTHONUTF8="1"

# Run FastAPI production server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
