import json
import re
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app import db
from app.models import Task

def register(client, email="student@example.com", password="password123"):
    return client.post("/register", data={"email": email, "password": password}, follow_redirects=True)


def login(client, email="student@example.com", password="password123"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def create_task(client, title="Deploy CloudTask", description="Run the pipeline", **fields):
    data = {"title": title, "description": description}
    data.update(fields)
    return client.post(
        "/tasks/new",
        data=data,
        follow_redirects=True,
    )


@pytest.fixture
def authenticated_client(client):
    register(client)
    return client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}
    assert response.headers["X-CloudTask-Version"] == "local"


def test_version_endpoint_returns_build_metadata(client, monkeypatch):
    monkeypatch.setenv("CLOUDTASK_BUILD_NUMBER", "42")
    monkeypatch.setenv("CLOUDTASK_GIT_COMMIT", "abc123")
    monkeypatch.setenv("CLOUDTASK_BUILD_TIME", "2026-11-15T12:00:00Z")

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json == {
        "build_number": "42",
        "git_commit": "abc123",
        "build_time": "2026-11-15T12:00:00Z",
    }


def metric_value(body, metric_name):
    match = re.search(rf"^{re.escape(metric_name)}\s+([0-9.]+)$", body, re.MULTILINE)
    return float(match.group(1)) if match else 0.0


def test_metrics_endpoint_reports_requests_duration_and_no_user_data(authenticated_client):
    client = authenticated_client
    response = client.get("/health")
    assert response.status_code == 200

    metrics_response = client.get("/metrics")
    metrics = metrics_response.data.decode()

    assert metrics_response.status_code == 200
    assert 'cloudtask_http_requests_total{endpoint="/health",method="GET",status="200"}' in metrics
    assert "cloudtask_http_request_duration_seconds_bucket" in metrics
    assert "student@example.com" not in metrics


def test_task_metrics_count_events_and_open_tasks(authenticated_client):
    client = authenticated_client
    before = client.get("/metrics").data.decode()
    created_before = metric_value(before, "cloudtask_tasks_created_total")
    completed_before = metric_value(before, "cloudtask_tasks_completed_total")
    deleted_before = metric_value(before, "cloudtask_tasks_deleted_total")

    create_task(client, title="Metrics task")
    after_create = client.get("/metrics").data.decode()
    assert metric_value(after_create, "cloudtask_tasks_created_total") > created_before
    assert "cloudtask_open_tasks 1.0" in after_create

    client.post("/tasks/1/toggle")
    after_complete = client.get("/metrics").data.decode()
    assert metric_value(after_complete, "cloudtask_tasks_completed_total") > completed_before
    assert "cloudtask_open_tasks 0.0" in after_complete

    client.post("/tasks/1/delete")
    after_delete = client.get("/metrics").data.decode()
    assert metric_value(after_delete, "cloudtask_tasks_deleted_total") > deleted_before


def test_stats_route_sends_statuses_and_renders_mocked_result(authenticated_client, monkeypatch):
    client = authenticated_client
    create_task(client, title="Pending task")
    create_task(client, title="Completed task")
    client.post("/tasks/2/toggle")
    monkeypatch.setenv("STATS_API_URL", "https://stats.example.test/stats")

    mocked_response = MagicMock()
    mocked_response.status = 200
    mocked_response.read.return_value = json.dumps({
        "completed": 1,
        "pending": 1,
        "total": 2,
        "completion_percentage": 50.0,
    }).encode("utf-8")
    mocked_response.__enter__.return_value = mocked_response

    with patch("app.tasks.urlopen", return_value=mocked_response) as mocked_urlopen:
        response = client.get("/stats")

    assert response.status_code == 200
    assert b"Completed" in response.data
    assert b"50.0%" in response.data
    request = mocked_urlopen.call_args.args[0]
    assert request.full_url == "https://stats.example.test/stats"
    assert json.loads(request.data) == ["pending", "completed"]


def test_stats_route_uses_local_counts_without_stats_api(authenticated_client, monkeypatch):
    client = authenticated_client
    create_task(client, title="Pending task")
    create_task(client, title="Completed task")
    client.post("/tasks/2/toggle")
    monkeypatch.delenv("STATS_API_URL", raising=False)

    response = client.get("/stats")

    assert response.status_code == 200
    assert b"Completed" in response.data
    assert b"50.0%" in response.data


def test_task_count_uses_singular_form_for_one_open_task(authenticated_client):
    create_task(authenticated_client, title="One open task")

    response = authenticated_client.get("/")

    assert b"1 open task to move forward." in response.data
    assert b"1 open tasks" not in response.data


def test_task_metadata_is_saved_and_displayed(authenticated_client):
    client = authenticated_client
    today = date.today().isoformat()
    create_task(
        client,
        title="Final exam",
        priority="high",
        category="Exam",
        due_date=today,
    )

    response = client.get("/")

    assert b"priority-high" in response.data
    assert b">Exam</span>" in response.data
    assert b">today</strong>" in response.data
    with client.application.app_context():
        task = db.session.get(Task, 1)
        assert task.priority == "high"
        assert task.category == "Exam"
        assert task.due_date == date.today()

    response = client.post(
        "/tasks/1/edit",
        data={
            "title": "Final exam revised",
            "description": "Updated",
            "priority": "low",
            "category": "Assignment",
            "due_date": "",
        },
        follow_redirects=True,
    )
    assert b"priority-low" in response.data
    assert b">Assignment</span>" in response.data


def test_task_filters_are_scoped_and_bookmarkable(authenticated_client):
    client = authenticated_client
    create_task(client, title="Math exam", category="Exam", priority="high")
    create_task(client, title="Build project", category="Project", priority="low")
    client.post("/tasks/2/toggle")

    response = client.get("/?q=exam&status=open&priority=high&category=Exam&sort=priority")

    assert b"Math exam" in response.data
    assert b"Build project" not in response.data


def test_task_sorting_by_due_date_and_priority(authenticated_client):
    client = authenticated_client
    create_task(
        client,
        title="Later task",
        priority="low",
        due_date=(date.today() + timedelta(days=5)).isoformat(),
    )
    create_task(
        client,
        title="Soon task",
        priority="high",
        due_date=(date.today() + timedelta(days=1)).isoformat(),
    )

    response = client.get("/?sort=due_date")
    html = response.data.decode()
    assert html.index("Soon task") < html.index("Later task")

    response = client.get("/?sort=priority")
    html = response.data.decode()
    assert html.index("Soon task") < html.index("Later task")


def test_overdue_open_tasks_are_highlighted(authenticated_client):
    create_task(
        authenticated_client,
        title="Late assignment",
        due_date=(date.today() - timedelta(days=1)).isoformat(),
    )

    response = authenticated_client.get("/")

    assert b"is-overdue" in response.data
    assert b">overdue</strong>" in response.data


def test_registration_logs_user_in_and_rejects_duplicates(client):
    response = register(client)
    assert response.status_code == 200
    assert b"My tasks" in response.data

    client.post("/logout")
    response = register(client)
    assert b"already registered" in response.data


def test_login_and_logout(client):
    register(client)
    client.post("/logout")

    response = login(client)
    assert response.status_code == 200
    assert b"My tasks" in response.data

    response = client.post("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Sign in" in response.data


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/"),
        ("get", "/stats"),
        ("get", "/tasks/new"),
        ("post", "/tasks/new"),
        ("get", "/tasks/1/edit"),
        ("post", "/tasks/1/toggle"),
        ("post", "/tasks/1/delete"),
    ],
)
def test_protected_routes_redirect_when_logged_out(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert "/login?next=" in response.headers["Location"]


def test_user_can_create_edit_complete_and_delete_task(authenticated_client):
    client = authenticated_client
    response = create_task(client)
    assert response.status_code == 200
    assert b"Deploy CloudTask" in response.data

    response = client.post(
        "/tasks/1/edit",
        data={"title": "Ship CloudTask", "description": "Run all pipeline gates"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Ship CloudTask" in response.data
    assert b"Run all pipeline gates" in response.data

    client.post("/tasks/1/toggle", follow_redirects=True)
    response = client.get("/")
    assert b"completed" in response.data

    response = client.post("/tasks/1/delete", follow_redirects=True)
    assert b"Deploy CloudTask" not in response.data


def test_invalid_login_is_rejected(client):
    register(client)
    client.post("/logout")
    response = login(client, password="wrongpass")
    assert b"Invalid email or password" in response.data


def test_user_cannot_see_or_modify_another_users_tasks(client):
    register(client, email="owner@example.com")
    create_task(client, title="Owner private task")
    client.post("/logout")

    register(client, email="other@example.com")
    response = client.get("/")
    assert b"Owner private task" not in response.data

    for path, data in [
        ("/tasks/1/edit", {"title": "Stolen task", "description": "No access"}),
        ("/tasks/1/toggle", {}),
        ("/tasks/1/delete", {}),
    ]:
        response = client.post(path, data=data)
        assert response.status_code == 404

    client.post("/logout")
    login(client, email="owner@example.com")
    response = client.get("/")
    assert b"Owner private task" in response.data
