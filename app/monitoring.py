import os
import time

from flask import Blueprint, Response, g, jsonify, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)
from prometheus_client.core import GaugeMetricFamily
from prometheus_client import multiprocess

from app import db
from app.models import Task
from app.version import build_info

metrics_bp = Blueprint("metrics", __name__)
REQUESTS = Counter(
    "cloudtask_http_requests_total",
    "Total HTTP requests handled by CloudTask.",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "cloudtask_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "endpoint"],
)
TASKS_CREATED = Counter("cloudtask_tasks_created_total", "Tasks created.")
TASKS_COMPLETED = Counter("cloudtask_tasks_completed_total", "Tasks marked completed.")
TASKS_DELETED = Counter("cloudtask_tasks_deleted_total", "Tasks deleted.")


class OpenTasksCollector:
    def collect(self):
        yield GaugeMetricFamily(
            "cloudtask_open_tasks",
            "Current number of open tasks.",
            value=Task.query.filter_by(completed=False).count(),
        )


def _endpoint_name():
    return request.url_rule.rule if request.url_rule else "unknown"


def _metrics_registry():
    registry = CollectorRegistry()
    if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
        multiprocess.MultiProcessCollector(registry)
    else:
        for collector in (
            REQUESTS,
            REQUEST_DURATION,
            TASKS_CREATED,
            TASKS_COMPLETED,
            TASKS_DELETED,
        ):
            registry.register(collector)
    registry.register(OpenTasksCollector())
    return registry


@metrics_bp.before_app_request
def start_request_timer():
    g.cloudtask_request_started_at = time.perf_counter()


@metrics_bp.after_app_request
def record_request(response):
    endpoint = _endpoint_name()
    REQUESTS.labels(request.method, endpoint, str(response.status_code)).inc()
    REQUEST_DURATION.labels(request.method, endpoint).observe(
        time.perf_counter() - g.cloudtask_request_started_at
    )
    return response


@metrics_bp.get("/health")
def health():
    response = jsonify(status="ok")
    response.headers["X-CloudTask-Version"] = os.getenv("CLOUDTASK_VERSION", "local")
    return response, 200


@metrics_bp.get("/metrics")
def metrics():
    return Response(generate_latest(_metrics_registry()), mimetype=CONTENT_TYPE_LATEST)


@metrics_bp.get("/version")
def version():
    return jsonify(build_info())
