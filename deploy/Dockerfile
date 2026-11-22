FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN groupadd --gid 10001 ds03 && useradd --uid 10001 --gid ds03 ds03 \
    && mkdir /data && chown ds03:ds03 /data
COPY src/ ./src/
COPY scripts/ ./scripts/
USER ds03
CMD ["python", "-m", "src.main", "identity"]
