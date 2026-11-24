FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
# Keep the schema SQL beside the Python module that loads it at startup.
RUN pip install --no-cache-dir --editable ".[cloud,mcp,semantic]" \
    && useradd --create-home --shell /usr/sbin/nologin tm \n    && mkdir -p /home/tm/.cache/huggingface && chown -R tm:tm /home/tm/.cache
ENV HF_HOME=/home/tm/.cache/huggingface
USER tm
