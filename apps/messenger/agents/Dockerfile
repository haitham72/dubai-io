# Mirsal agents service. Local first: `docker compose up` from agents/ (service + Redis).
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mirsal_agents ./mirsal_agents
COPY watchlist.json .
RUN useradd --create-home mirsal && mkdir -p /data /secrets && chown mirsal /data /secrets
USER mirsal
ENV AGENTS_DATA_DIR=/data GMAIL_CLIENT_FILE=/secrets/gmail_client.json GMAIL_TOKEN_FILE=/secrets/gmail_token.json
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8787/agents/health')"
CMD ["uvicorn", "mirsal_agents.app:app", "--host", "0.0.0.0", "--port", "8787"]
