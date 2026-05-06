from unittest.mock import patch

from meghyan_portal.app import app
from meghyan_portal.portal_state import reset_demo_rate_limit


def login(client, email: str = "admin@meghyan.ai", password: str = "admin-demo") -> None:
    response = client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_landing_page_renders() -> None:
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"MeghyanAI" in response.data


def test_login_page_shows_demo_credentials() -> None:
    client = app.test_client()
    response = client.get("/login")
    assert response.status_code == 200
    assert b"admin@meghyan.ai" in response.data


def test_pricing_page_renders_packages() -> None:
    client = app.test_client()
    response = client.get("/pricing")
    assert response.status_code == 200
    assert b"Red Team Scan" in response.data
    assert b"Scenario API" in response.data
    assert b"Certification Pack" in response.data


def test_dashboard_shows_redteam_section_for_redteam_user() -> None:
    client = app.test_client()
    login(client, email="redteam@client.ai", password="rt-demo")
    response = client.get("/app")
    assert response.status_code == 200
    assert b"Red Team" in response.data


def test_assistant_endpoint_returns_analysis() -> None:
    client = app.test_client()
    login(client)
    response = client.post("/api/assistant/query", json={"prompt": "Why is Monte Carlo ahead?"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert "answer" in payload
    assert "chart_points" in payload
    assert "thread" in payload


def test_assistant_thread_continues_and_switches_mode() -> None:
    client = app.test_client()
    login(client)
    first = client.post("/api/assistant/query", json={"prompt": "Internal diagnosis", "mode": "internal"})
    first_payload = first.get_json()
    thread_id = first_payload["thread"]["thread_id"]
    second = client.post(
        "/api/assistant/query",
        json={"prompt": "Rewrite for customer", "mode": "customer", "thread_id": thread_id},
    )
    second_payload = second.get_json()
    assert second.status_code == 200
    assert second_payload["mode"] == "customer"
    assert second_payload["thread"]["thread_id"] == thread_id
    assert second_payload["thread"]["mode"] == "customer"
    assert len(second_payload["thread"]["messages"]) >= 4


def test_verification_request_redirects_to_detail() -> None:
    client = app.test_client()
    login(client)
    response = client.post(
        "/app/reports/request-verification",
        data={"model_name": "Policy A", "scope": "Formal verification"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/app/verification/" in response.headers["Location"]


@patch("meghyan_portal.app.run_quantum_tree_pipeline")
def test_demo_endpoint_returns_live_contract(mock_run) -> None:
    mock_run.return_value = {
        "failure_rate": 0.24,
        "teacher_accuracy": 0.925,
        "quantum_backend": "qiskit-statevector",
        "student_mse": 0.007,
        "failures_found": 3,
        "top_failures": [{"type": "collision-risk", "severity": "high", "description": "Loss of separation forecast."}],
    }
    client = app.test_client()
    remote = {"REMOTE_ADDR": "203.0.113.10"}
    reset_demo_rate_limit(remote["REMOTE_ADDR"])
    response = client.post("/api/demo/run", json={"scenario_type": "collision"}, environ_base=remote)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["scenario_type"] == "collision"
    assert 0 <= payload["risk_score"] <= 100
    assert payload["quantum_backend"] == "qiskit-statevector"
    assert round(payload["teacher_accuracy"], 3) == 0.925
    assert isinstance(payload["top_failures"], list)


@patch("meghyan_portal.app.run_quantum_tree_pipeline")
def test_demo_endpoint_is_rate_limited_after_three_runs(mock_run) -> None:
    mock_run.return_value = {
        "failure_rate": 0.1,
        "teacher_accuracy": 0.93,
        "quantum_backend": "qiskit-statevector",
        "student_mse": 0.01,
        "failures_found": 1,
        "top_failures": [],
    }
    client = app.test_client()
    remote = {"REMOTE_ADDR": "198.51.100.23"}
    reset_demo_rate_limit(remote["REMOTE_ADDR"])
    for _ in range(3):
        response = client.post("/api/demo/run", json={"scenario_type": "separation"}, environ_base=remote)
        assert response.status_code == 200
    blocked = client.post("/api/demo/run", json={"scenario_type": "separation"}, environ_base=remote)
    assert blocked.status_code == 429
    payload = blocked.get_json()
    assert "Rate limit reached" in payload["error"]


@patch("meghyan_portal.app.run_quantum_tree_pipeline")
def test_demo_endpoint_requires_no_auth(mock_run) -> None:
    mock_run.return_value = {
        "failure_rate": 0.15,
        "teacher_accuracy": 0.91,
        "quantum_backend": "qiskit-statevector",
        "student_mse": 0.02,
        "failures_found": 2,
        "top_failures": [],
    }
    client = app.test_client()
    remote = {"REMOTE_ADDR": "192.0.2.55"}
    reset_demo_rate_limit(remote["REMOTE_ADDR"])
    response = client.post("/api/demo/run", json={"scenario_type": "obstacle"}, environ_base=remote)
    assert response.status_code == 200
    assert response.get_json()["scenario_type"] == "obstacle"


def test_api_user_can_download_scenarios() -> None:
    client = app.test_client()
    login(client, email="api@client.ai", password="api-demo")
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    assert "attachment; filename=scenarios.json" in response.headers["Content-Disposition"]


def test_enterprise_user_can_download_report() -> None:
    client = app.test_client()
    login(client, email="enterprise@client.ai", password="ent-demo")
    response = client.get("/api/report/latest")
    assert response.status_code == 200
    assert "attachment; filename=quantum_tree_results.json" in response.headers["Content-Disposition"]
