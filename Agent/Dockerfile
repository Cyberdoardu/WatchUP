FROM python:3.13.2-slim

RUN apt-get update && apt-get install -y \
    curl \
    dnsutils \
    telnet \
    netcat-openbsd \
    iputils-ping \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py .

ENV CENTRAL_SERVER_URL="http://central-server:5000"
ENV AGENT_NAME="agent-01"
ENV CHECK_INTERVAL=30

CMD ["python", "agent.py"]