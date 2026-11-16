import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _json_response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _statuses_from_event(event):
    payload = event
    if isinstance(event, dict) and "body" in event:
        payload = event["body"]
        if isinstance(payload, str):
            payload = json.loads(payload)
    if not isinstance(payload, list):
        raise ValueError("request body must be a JSON list of statuses")
    if any(status not in {"completed", "pending"} for status in payload):
        raise ValueError("statuses must be completed or pending")
    return payload


def handler(event, context):
    try:
        statuses = _statuses_from_event(event)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        logger.warning(json.dumps({"event": "invalid_request", "error": str(error)}))
        return _json_response(400, {"error": str(error)})

    completed = statuses.count("completed")
    pending = statuses.count("pending")
    total = len(statuses)
    completion_percentage = round((completed / total) * 100, 2) if total else 0.0
    result = {
        "completed": completed,
        "pending": pending,
        "total": total,
        "completion_percentage": completion_percentage,
    }
    logger.info(json.dumps({"event": "task_stats_calculated", **result}))
    return _json_response(200, result)
