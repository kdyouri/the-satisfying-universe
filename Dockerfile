FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONTZPATH=""
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 tsu && useradd --uid 10001 --gid tsu --create-home tsu
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY tsu tsu
COPY migrations migrations
COPY alembic.ini .
RUN mkdir /data && chown tsu:tsu /data
USER tsu
CMD ["uvicorn", "tsu.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
