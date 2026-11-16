import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

handler_module_spec = spec_from_file_location("stats_handler", Path(__file__).with_name("stats_handler.py"))
handler_module = module_from_spec(handler_module_spec)
handler_module_spec.loader.exec_module(handler_module)
handler = handler_module.handler


def test_handler_counts_statuses():
    response = handler({"body": json.dumps(["completed", "pending", "completed"])}, None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "completed": 2,
        "pending": 1,
        "total": 3,
        "completion_percentage": 66.67,
    }


def test_handler_rejects_invalid_status():
    response = handler(["blocked"], None)
    assert response["statusCode"] == 400
