FROM python:3.11-slim AS builder

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /build

RUN python -m venv "$VIRTUAL_ENV"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

ARG BUILD_NUMBER=local
ARG GIT_COMMIT=unknown
ARG BUILD_TIME=unknown
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus \
    CLOUDTASK_BUILD_NUMBER="${BUILD_NUMBER}" \
    CLOUDTASK_GIT_COMMIT="${GIT_COMMIT}" \
    CLOUDTASK_BUILD_TIME="${BUILD_TIME}"
WORKDIR /app

RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY migrations ./migrations
COPY run.py .
COPY docker/entrypoint.sh ./docker/entrypoint.sh
RUN mkdir -p /app/instance \
    && chown -R appuser:appgroup /app

USER appuser
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health')"
ENTRYPOINT ["sh", "./docker/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "run:app"]