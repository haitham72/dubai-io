FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
# Keep the schema SQL beside the Python module that loads it at startup.
RUN pip install --no-cache-dir --editable ".[cloud,mcp]" \
    && useradd --create-home --shell /usr/sbin/nologin tm
USER tm
