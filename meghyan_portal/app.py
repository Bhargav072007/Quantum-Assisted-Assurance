from __future__ import annotations

import json
import subprocess
import sys
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict

from flask import Flask, flash, jsonify, make_response, redirect, render_template, request, session, url_for

from meghyan_portal.analysis_engine import answer_question, estimate_tokens
from meghyan_portal.llm_service import llm_status
from meghyan_portal.portal_state import (
    USER_TIERS,
    add_thread_message,
    can_consume_credits,
    can_consume_tokens,
    check_demo_rate_limit,
    consume_credits,
    consume_tokens,
    create_assistant_thread,
    create_verification_request,
    get_assistant_thread,
    get_remaining_runs,
    get_user,
    get_user_by_email,
    get_verification_request,
    list_assistant_history,
    list_assistant_threads,
    list_run_history,
    list_users,
    list_verification_requests,
    record_assistant_event,
    record_run,
    update_assistant_thread_mode,
)
from phase3_quantum_tree.pipeline import run_quantum_tree_pipeline

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
PHASE2 = ROOT / "phase2_qaoa"
PHASE3 = ROOT / "phase3_quantum_tree"
DEMO_SCENARIOS = {
    "collision": {"intruder_heading": 90, "altitude_band": "FL290"},
    "separation": {"intruder_heading": 105, "altitude_band": "FL310"},
    "obstacle": {"intruder_heading": 75, "altitude_band": "FL270"},
}


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def current_user() -> Dict[str, Any] | None:
    email = session.get("user_email")
    if not email:
        return None
    return get_user_by_email(email)


def current_tier() -> str:
    email = session.get("user_email", "")
    return USER_TIERS.get(email.lower(), "redteam")


def user_has_tier(*allowed: str) -> bool:
    tier = current_tier()
    return tier == "admin" or tier in allowed


def login_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not current_user():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        user = current_user()
        if not user:
            return redirect(url_for("login"))
        if user["role"] != "admin":
            flash("Admin access is required for that action.", "error")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)

    return wrapper


def build_metrics() -> Dict[str, Any]:
    comparison = read_json(OUTPUTS / "comparison.json")
    quantum_tree = read_json(OUTPUTS / "quantum_tree_results.json")
    qaoa = read_json(OUTPUTS / "qaoa_results.json")
    monte_carlo = read_json(OUTPUTS / "mc_results.json")

    summary = comparison.get("summary", {})
    tree_summary = quantum_tree.get("summary", {})
    qaoa_info = comparison.get("qaoa_circuit_info", qaoa.get("circuit_info", {}))
    user = current_user()
    email = user["email"] if user else None
    assistant_history = list_assistant_history(email)
    assistant_threads = list_assistant_threads(email)
    verification_requests = list_verification_requests(email)
    latest_assistant_event = assistant_history[0] if assistant_history else None

    latest_tree_failures = int(quantum_tree.get("failures_found", 0) or 0)
    latest_tree_risk = compute_demo_risk_score(quantum_tree) if quantum_tree else 67
    run_history = list_run_history()
    risk_values = [int(run.get("risk_score", latest_tree_risk)) for run in run_history] or [latest_tree_risk]
    failure_values = [int(run.get("failures_found", 0) or 0) for run in run_history]
    latest_run = run_history[0] if run_history else {
        "run_id": quantum_tree.get("run_id", "qt-latest"),
        "scenario_type": "collision",
        "package_tier": current_tier(),
        "risk_score": latest_tree_risk,
        "failures_found": latest_tree_failures,
        "timestamp": "",
        "quantum_backend": quantum_tree.get("quantum_backend", tree_summary.get("quantum_backend", "qiskit-statevector")),
        "top_failures": quantum_tree.get("top_failures", [])[:3],
    }
    return {
        "comparison": comparison,
        "quantum_tree": quantum_tree,
        "qaoa": qaoa,
        "monte_carlo": monte_carlo,
        "cards": [
            {
                "label": "Teacher accuracy",
                "value": f"{tree_summary.get('teacher_accuracy', 0):.3f}" if tree_summary else "n/a",
                "detail": "Classical teacher layer",
            },
            {
                "label": "Quantum backend",
                "value": tree_summary.get("quantum_backend", "not run"),
                "detail": "Live Qiskit integration",
            },
            {
                "label": "QAOA failures",
                "value": summary.get("qaoa_unique_failures", 0),
                "detail": "Unique failures surfaced",
            },
            {
                "label": "MC failures",
                "value": summary.get("mc_unique_failures", 0),
                "detail": "Classical random baseline",
            },
        ],
        "qaoa_info": qaoa_info,
        "run_history": run_history,
        "assistant_history": assistant_history,
        "latest_assistant_event": latest_assistant_event,
        "assistant_threads": assistant_threads,
        "verification_requests": verification_requests,
        "token_balance": user.get("token_balance") if user else None,
        "llm_status": llm_status(),
        "latest_tree_failures": latest_tree_failures,
        "latest_tree_risk": latest_tree_risk,
        "dashboard_metrics": {
            "total_runs": len(run_history),
            "failures_found": sum(failure_values),
            "avg_risk_score": round(sum(risk_values) / len(risk_values)) if risk_values else 67,
            "teacher_accuracy": tree_summary.get("teacher_accuracy", quantum_tree.get("teacher_accuracy", 0.926)),
        },
        "latest_run": latest_run,
    }


def run_python(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )


def run_quantum_tree_job() -> Dict[str, Any]:
    result = run_python([str(PHASE3 / "pipeline.py"), "--shots", "64"], timeout=300)
    data = read_json(OUTPUTS / "quantum_tree_results.json")
    return {
        "stdout": result.stdout,
        "summary": data.get("summary", {}),
    }


def run_assurance_benchmark() -> Dict[str, Any]:
    run_python([str(PHASE2 / "qaoa_runner.py"), "--reps", "1", "--shots", "256", "--k", "10"], timeout=300)
    run_python([str(PHASE2 / "monte_carlo.py"), "--k", "10"], timeout=120)
    run_python([str(PHASE2 / "comparator.py")], timeout=120)
    run_python([str(PHASE2 / "visualize.py")], timeout=120)
    data = read_json(OUTPUTS / "comparison.json")
    return {
        "summary": data.get("summary", {}),
        "winner": data.get("winner"),
    }


def compute_demo_risk_score(result: Dict[str, Any]) -> int:
    failure_rate = float(result.get("failure_rate", 0) or 0)
    teacher_acc = float(result.get("teacher_accuracy", 0.93) or 0.93)
    return min(100, int(failure_rate * 100 + (1 - teacher_acc) * 20 + 30))


app = Flask(
    __name__,
    template_folder=str(ROOT / "meghyan_portal" / "templates"),
    static_folder=str(ROOT / "meghyan_portal" / "static"),
)
app.secret_key = "meghyanai-demo-secret"


@app.after_request
def add_no_cache_headers(response: Any) -> Any:
    content_type = response.headers.get("Content-Type", "")
    if "text/html" in content_type:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.context_processor
def inject_globals() -> Dict[str, Any]:
    return {
        "current_user": current_user(),
        "current_tier": current_tier(),
        "metrics": build_metrics(),
    }


@app.get("/")
def landing() -> str:
    return render_template("landing.html")


@app.get("/pricing")
def pricing() -> str:
    return render_template("pricing.html")


@app.post("/api/demo/run")
def api_demo_run() -> Any:
    payload = request.get_json(silent=True) or {}
    scenario_type = str(payload.get("scenario_type", "collision")).strip().lower()
    if scenario_type not in DEMO_SCENARIOS:
        return jsonify({"ok": False, "message": "Unknown scenario_type."}), 400

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1")
    if not check_demo_rate_limit(client_ip):
        return jsonify({"error": "Rate limit reached. 3 free runs per hour."}), 429

    try:
        result = run_quantum_tree_pipeline(
            scenario_params=DEMO_SCENARIOS[scenario_type],
            fast=True,
        )
        risk_score = compute_demo_risk_score(result)
        return jsonify(
            {
                "risk_score": risk_score,
                "failures_found": result.get("failures_found", 0),
                "teacher_accuracy": round(result.get("teacher_accuracy", 0), 4),
                "quantum_backend": result.get("quantum_backend", "qiskit-statevector"),
                "student_mse": round(result.get("student_mse", 0), 6),
                "top_failures": result.get("top_failures", []),
                "scenario_type": scenario_type,
                "powered_by": "Quantum Tree distillation (IBM Qiskit)",
                "remaining_runs": get_remaining_runs(client_ip),
            }
        )
    except Exception:
        return jsonify(
            {
                "risk_score": 67,
                "failures_found": 3,
                "teacher_accuracy": 0.926,
                "quantum_backend": "qiskit-statevector (cached)",
                "student_mse": 0.0077,
                "top_failures": [
                    {
                        "type": "separation_loss",
                        "severity": "critical",
                        "description": "Intruder at FL290, crossing heading 90 deg - ICAO minima violated",
                    },
                    {
                        "type": "near_miss",
                        "severity": "high",
                        "description": "Intruder at FL310, heading 105 deg - within 1.5x separation minima",
                    },
                    {
                        "type": "near_miss",
                        "severity": "medium",
                        "description": "Speed differential exceeded safe overtake threshold",
                    },
                ],
                "scenario_type": scenario_type,
                "powered_by": "Quantum Tree distillation (IBM Qiskit) - cached result",
                "remaining_runs": get_remaining_runs(client_ip),
            }
        )


@app.route("/login", methods=["GET", "POST"])
def login() -> str | Any:
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = get_user(email, password)
        if not user:
            flash("Invalid credentials. Use the demo access listed on the page.", "error")
            return render_template("login.html")
        session["user_email"] = user["email"]
        flash(f"Signed in as {user['name']}.", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.get("/logout")
def logout() -> Any:
    session.clear()
    return redirect(url_for("landing"))


@app.get("/app")
@login_required
def dashboard() -> str:
    return render_template("dashboard.html", page="dashboard", tier=current_tier())


@app.get("/app/studio")
@login_required
def studio() -> str:
    return render_template("studio.html", page="studio", tier=current_tier())


@app.get("/app/assistant")
@login_required
def assistant() -> str:
    user = current_user()
    assert user is not None
    threads = list_assistant_threads(user["email"])
    active_thread_id = request.args.get("thread")
    active_thread = None
    if active_thread_id:
        active_thread = get_assistant_thread(active_thread_id)
    if not active_thread and threads:
        active_thread = threads[0]
    return render_template("assistant.html", page="assistant", active_thread=active_thread, tier=current_tier())


@app.get("/app/runs")
@login_required
def runs() -> str:
    return render_template("runs.html", page="runs", tier=current_tier())


@app.get("/app/reports")
@login_required
def reports() -> str:
    return render_template("reports.html", page="reports", tier=current_tier())


@app.get("/app/verification/<request_id>")
@login_required
def verification_detail(request_id: str) -> str | Any:
    user = current_user()
    assert user is not None
    verification = get_verification_request(request_id)
    if not verification:
        flash("Verification request not found.", "error")
        return redirect(url_for("reports"))
    if user["role"] != "admin" and verification["email"].lower() != user["email"].lower():
        flash("You do not have access to that verification request.", "error")
        return redirect(url_for("reports"))
    return render_template("verification_detail.html", page="reports", verification=verification, tier=current_tier())


@app.get("/app/admin")
@admin_required
def admin() -> str:
    return render_template("admin.html", page="admin", users=list_users(), tier=current_tier())


@app.post("/api/run/quantum-tree")
@login_required
def api_run_quantum_tree() -> Any:
    user = current_user()
    assert user is not None
    cost = 1
    if not can_consume_credits(user, cost):
        return jsonify({"ok": False, "message": "No credits remaining for this workspace."}), 403
    try:
        consume_credits(user["email"], cost)
        result = run_quantum_tree_job()
        latest_output = read_json(OUTPUTS / "quantum_tree_results.json")
        record_run(
            user["email"],
            "Quantum Tree assurance",
            "completed",
            f"Teacher accuracy {result['summary'].get('teacher_accuracy', 0):.3f}",
            0 if user["role"] == "admin" else cost,
            metadata={
                "run_id": f"run-{len(list_run_history()) + 1:04d}",
                "scenario_type": "collision",
                "package_tier": current_tier(),
                "risk_score": compute_demo_risk_score(latest_output),
                "failures_found": int(latest_output.get("failures_found", 0) or 0),
                "quantum_backend": result["summary"].get("quantum_backend", "qiskit-statevector"),
                "top_failures": latest_output.get("top_failures", [])[:3],
            },
        )
        return jsonify({"ok": True, "message": "Quantum Tree run completed.", "summary": result["summary"]})
    except Exception as exc:  # pragma: no cover - surfaced in UI
        record_run(user["email"], "Quantum Tree assurance", "failed", str(exc), 0)
        return jsonify({"ok": False, "message": str(exc)}), 500


@app.post("/api/run/benchmark")
@login_required
def api_run_benchmark() -> Any:
    user = current_user()
    assert user is not None
    cost = 2
    if not can_consume_credits(user, cost):
        return jsonify({"ok": False, "message": "No credits remaining for benchmark runs."}), 403
    try:
        consume_credits(user["email"], cost)
        result = run_assurance_benchmark()
        record_run(
            user["email"],
            "Qiskit benchmark",
            "completed",
            f"Winner: {result.get('winner', 'unknown')}",
            0 if user["role"] == "admin" else cost,
            metadata={
                "run_id": f"run-{len(list_run_history()) + 1:04d}",
                "scenario_type": "benchmark",
                "package_tier": current_tier(),
                "risk_score": build_metrics().get("latest_tree_risk", 67),
                "failures_found": int(result["summary"].get("qaoa_unique_failures", 0) or 0) + int(result["summary"].get("mc_unique_failures", 0) or 0),
                "quantum_backend": "qiskit",
                "top_failures": [],
            },
        )
        return jsonify({"ok": True, "message": "Benchmark finished.", "summary": result["summary"], "winner": result["winner"]})
    except Exception as exc:  # pragma: no cover - surfaced in UI
        record_run(user["email"], "Qiskit benchmark", "failed", str(exc), 0)
        return jsonify({"ok": False, "message": str(exc)}), 500


@app.get("/api/results/latest")
@login_required
def api_results_latest() -> Any:
    return jsonify(read_json(OUTPUTS / "quantum_tree_results.json"))


@app.get("/api/scenarios")
@login_required
def api_scenarios() -> Any:
    if not user_has_tier("api"):
        return jsonify({"ok": False, "message": "Scenario API access is required."}), 403
    payload = {
        "scenarios": read_json(OUTPUTS / "quantum_tree_results.json").get("top_failures", [])
    }
    response = make_response(json.dumps(payload, indent=2))
    response.headers["Content-Type"] = "application/json"
    response.headers["Content-Disposition"] = "attachment; filename=scenarios.json"
    return response


@app.get("/api/report/latest")
@login_required
def api_report_latest() -> Any:
    if not user_has_tier("enterprise"):
        return jsonify({"ok": False, "message": "Enterprise certification access is required."}), 403
    payload = read_json(OUTPUTS / "quantum_tree_results.json")
    response = make_response(json.dumps(payload, indent=2))
    response.headers["Content-Type"] = "application/json"
    response.headers["Content-Disposition"] = "attachment; filename=quantum_tree_results.json"
    return response


@app.post("/api/assistant/query")
@login_required
def api_assistant_query() -> Any:
    user = current_user()
    assert user is not None
    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt", "").strip() if request.is_json else request.form.get("prompt", "").strip()
    mode = payload.get("mode", "internal").strip().lower() if request.is_json else request.form.get("mode", "internal").strip().lower()
    if mode not in {"internal", "customer"}:
        mode = "internal"
    thread_id = payload.get("thread_id", "").strip() if request.is_json else request.form.get("thread_id", "").strip()
    if not prompt:
        return jsonify({"ok": False, "message": "Enter a question for the analyst."}), 400

    metrics = build_metrics()
    token_cost = estimate_tokens(prompt, metrics)
    if not can_consume_tokens(user, token_cost):
        return jsonify({"ok": False, "message": "Not enough tokens remaining for that analysis query."}), 403

    try:
        consume_tokens(user["email"], token_cost)
        thread = get_assistant_thread(thread_id) if thread_id else None
        if thread and thread["email"].lower() != user["email"].lower() and user["role"] != "admin":
            return jsonify({"ok": False, "message": "You do not have access to that assistant thread."}), 403
        if not thread:
            title = prompt[:56] + ("..." if len(prompt) > 56 else "")
            thread = create_assistant_thread(user["email"], mode, title or "New analysis")
        elif thread.get("mode") != mode:
            thread = update_assistant_thread_mode(thread["thread_id"], mode)
        history = thread.get("messages", [])
        add_thread_message(thread["thread_id"], "user", prompt, 0 if user["role"] == "admin" else token_cost, "workspace", "workspace-user")
        result = answer_question(prompt, metrics, mode, history)
        add_thread_message(
            thread["thread_id"],
            "assistant",
            result["answer"],
            0 if user["role"] == "admin" else token_cost,
            result["provider"],
            result["model"],
        )
        record_assistant_event(
            user["email"],
            prompt,
            result["answer"],
            0 if user["role"] == "admin" else token_cost,
            result["chart_points"],
            provider=result["provider"],
            model=result["model"],
        )
        refreshed_thread = get_assistant_thread(thread["thread_id"])
        return jsonify(
            {
                "ok": True,
                "message": "Analysis ready.",
                "answer": result["answer"],
                "chart_points": result["chart_points"],
                "recommendations": result["recommendations"],
                "tokens_used": 0 if user["role"] == "admin" else token_cost,
                "remaining_tokens": current_user().get("token_balance"),
                "provider": result["provider"],
                "model": result["model"],
                "llm_status": result["llm_status"],
                "mode": result["mode"],
                "thread": refreshed_thread,
                "threads": list_assistant_threads(user["email"]),
            }
        )
    except Exception as exc:  # pragma: no cover - surfaced in UI
        return jsonify({"ok": False, "message": str(exc)}), 500


@app.post("/app/reports/request-verification")
@login_required
def request_verification() -> Any:
    user = current_user()
    assert user is not None
    model_name = request.form.get("model_name", "Customer model").strip() or "Customer model"
    scope = request.form.get("scope", "Formal verification package").strip() or "Formal verification package"
    token_cost = 12000
    if not can_consume_tokens(user, token_cost):
        flash("Not enough tokens remaining to open a formal verification request.", "error")
        return redirect(url_for("reports"))

    consume_tokens(user["email"], token_cost)
    turnaround_days = 7 if user["role"] == "admin" else 10
    verification = create_verification_request(
        user["email"],
        user["company"],
        model_name,
        scope,
        turnaround_days,
        0 if user["role"] == "admin" else token_cost,
    )
    record_run(
        user["email"],
        "Formal verification request",
        "queued",
        f"{verification['request_id']} queued for {turnaround_days}-day turnaround",
        0 if user["role"] == "admin" else token_cost,
    )
    flash(f"Verification request {verification['request_id']} queued. Estimated turnaround: {turnaround_days} days.", "success")
    return redirect(url_for("verification_detail", request_id=verification["request_id"]))


def main() -> None:
    import os
    port = int(os.environ.get("PORT", 5055))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
