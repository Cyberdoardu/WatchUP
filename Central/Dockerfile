FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends netcat-openbsd && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
    
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY central.py .

EXPOSE 5000

CMD ["sh", "-c", "while ! nc -z scylladb 9042; do sleep 2; done && python central.py"]