FROM python:3.11-slim

ARG BUILD_NUMBER=local
ARG GIT_COMMIT=unknown
ARG BUILD_TIME=unknown
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus \
    CLOUDTASK_BUILD_NUMBER="${BUILD_NUMBER}" \
    CLOUDTASK_GIT_COMMIT="${GIT_COMMIT}" \
    CLOUDTASK_BUILD_TIME="${BUILD_TIME}"
WORKDIR /app
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY migrations ./migrations
COPY run.py .
COPY docker/entrypoint.sh ./docker/entrypoint.sh
RUN mkdir -p /app/instance && chown -R appuser:appgroup /app
USER appuser
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health')"
ENTRYPOINT ["sh", "./docker/entrypoint.sh"]
CMD ["python", "run.py"]
