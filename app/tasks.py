import json
import os
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, or_

from app import db
from app.monitoring import TASKS_COMPLETED, TASKS_CREATED, TASKS_DELETED
from app.models import Task

tasks_bp = Blueprint("tasks", __name__)
PRIORITIES = ("low", "medium", "high")
STATUSES = ("open", "completed")


def _owned_task(task_id):
    return Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()


def _task_query():
    query = Task.query.filter_by(user_id=current_user.id)
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip().lower()
    priority = request.args.get("priority", "").strip().lower()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "").strip().lower()

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_pattern),
                Task.description.ilike(search_pattern),
                Task.category.ilike(search_pattern),
            )
        )
    if status == "open":
        query = query.filter_by(completed=False)
    elif status == "completed":
        query = query.filter_by(completed=True)
    if priority in PRIORITIES:
        query = query.filter_by(priority=priority)
    if category:
        query = query.filter(Task.category.ilike(category))

    if sort == "due_date":
        query = query.order_by(
            case((Task.due_date.is_(None), 1), else_=0),
            Task.due_date.asc(),
            Task.created_at.desc(),
        )
    elif sort == "priority":
        query = query.order_by(
            case(
                (Task.priority == "high", 0),
                (Task.priority == "medium", 1),
                else_=2,
            ),
            Task.created_at.desc(),
        )
    elif sort == "newest":
        query = query.order_by(Task.created_at.desc())
    else:
        query = query.order_by(Task.completed, Task.created_at.desc())
    return query


def _form_values(task=None):
    priority = request.form.get("priority", "medium").strip().lower()
    category = request.form.get("category", "Other").strip() or "Other"
    due_date_value = request.form.get("due_date", "").strip()
    due_date = None
    if due_date_value:
        try:
            due_date = date.fromisoformat(due_date_value)
        except ValueError:
            flash("Use a valid due date.", "error")
            return None
    if priority not in PRIORITIES:
        flash("Choose a low, medium, or high priority.", "error")
        return None
    return priority, category[:80], due_date


@tasks_bp.route("/")
@login_required
def index():
    tasks = _task_query().all()
    return render_template("tasks/index.html", tasks=tasks, stats=None, today=date.today())


def _request_stats(statuses):
    stats_api_url = os.getenv("STATS_API_URL", "").strip()
    if not stats_api_url:
        completed = statuses.count("completed")
        pending = statuses.count("pending")
        total = len(statuses)
        return {
            "completed": completed,
            "pending": pending,
            "total": total,
            "completion_percentage": round((completed / total) * 100, 2) if total else 0.0,
        }

    stats_request = Request(
        stats_api_url,
        data=json.dumps(statuses).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(stats_request, timeout=5) as response:
        if response.status >= 400:
            raise RuntimeError(f"Statistics API returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


@tasks_bp.get("/stats")
@login_required
def stats():
    tasks = _task_query().all()
    statuses = ["completed" if task.completed else "pending" for task in tasks]
    try:
        task_stats = _request_stats(statuses)
    except (HTTPError, URLError, RuntimeError, ValueError):
        flash("Task statistics are temporarily unavailable.", "error")
        task_stats = None
    return render_template("tasks/index.html", tasks=tasks, stats=task_stats, today=date.today())


@tasks_bp.route("/tasks/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        if not title:
            flash("A task title is required.", "error")
        else:
            values = _form_values()
            if values:
                priority, category, due_date = values
                db.session.add(
                    Task(
                        title=title,
                        description=description,
                        priority=priority,
                        category=category,
                        due_date=due_date,
                        user_id=current_user.id,
                    )
                )
                db.session.commit()
                TASKS_CREATED.inc()
                flash("Task added.", "success")
                return redirect(url_for("tasks.index"))
    return render_template("tasks/form.html", task=None)


@tasks_bp.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit(task_id):
    task = _owned_task(task_id)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("A task title is required.", "error")
        else:
            values = _form_values(task)
            if values:
                task.title = title
                task.description = request.form.get("description", "").strip()
                task.priority, task.category, task.due_date = values
                db.session.commit()
                flash("Task updated.", "success")
                return redirect(url_for("tasks.index"))
    return render_template("tasks/form.html", task=task)


@tasks_bp.post("/tasks/<int:task_id>/toggle")
@login_required
def toggle(task_id):
    task = _owned_task(task_id)
    task.completed = not task.completed
    db.session.commit()
    if task.completed:
        TASKS_COMPLETED.inc()
    return redirect(url_for("tasks.index"))


@tasks_bp.post("/tasks/<int:task_id>/delete")
@login_required
def delete(task_id):
    task = _owned_task(task_id)
    db.session.delete(task)
    db.session.commit()
    TASKS_DELETED.inc()
    flash("Task deleted.", "success")
    return redirect(url_for("tasks.index"))
