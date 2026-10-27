FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY backend/ ./

RUN uv pip install --system --no-cache -e ".[dev]"

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "src.boot"]
