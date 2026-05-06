from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from json import JSONDecodeError

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "outputs" / "portal_state.json"
USER_TIERS = {
    "admin@meghyan.ai": "admin",
    "redteam@client.ai": "redteam",
    "api@client.ai": "api",
    "enterprise@client.ai": "enterprise",
}
_rate_limits: defaultdict[str, list[datetime]] = defaultdict(list)

DEFAULT_STATE: Dict[str, Any] = {
    "users": [
        {
            "email": "admin@meghyan.ai",
            "password": "admin-demo",
            "name": "Platform Admin",
            "role": "admin",
            "company": "MeghyanAI",
            "credits": None,
            "token_balance": None,
            "status": "active",
        },
        {
            "email": "pilot@aerosafe.ai",
            "password": "pilot-demo",
            "name": "AeroSafe Pilot",
            "role": "customer",
            "company": "AeroSafe Labs",
            "credits": 6,
            "token_balance": 120000,
            "status": "active",
        },
        {
            "email": "redteam@client.ai",
            "password": "rt-demo",
            "name": "Red Team Client",
            "role": "customer",
            "company": "Client AI",
            "credits": 3,
            "token_balance": 50000,
            "status": "active",
            "package_tier": "redteam",
        },
        {
            "email": "api@client.ai",
            "password": "api-demo",
            "name": "Scenario API Client",
            "role": "customer",
            "company": "Client AI",
            "credits": 8,
            "token_balance": 90000,
            "status": "active",
            "package_tier": "api",
        },
        {
            "email": "enterprise@client.ai",
            "password": "ent-demo",
            "name": "Enterprise Client",
            "role": "customer",
            "company": "Client AI",
            "credits": 16,
            "token_balance": 250000,
            "status": "active",
            "package_tier": "enterprise",
        },
    ],
    "run_history": [],
    "assistant_history": [],
    "assistant_threads": [],
    "verification_requests": [],
    "demo_rate_limits": {},
}


def _merge_defaults(state: Dict[str, Any]) -> Dict[str, Any]:
    merged = json.loads(json.dumps(DEFAULT_STATE))
    merged.update(state)

    existing_users = state.get("users", [])
    default_users = {user["email"].lower(): user for user in DEFAULT_STATE["users"]}
    existing_by_email = {user["email"].lower(): user for user in existing_users if "email" in user}
    normalized_users = []
    for user in existing_users:
        base = dict(default_users.get(user["email"].lower(), {}))
        base.update(user)
        normalized_users.append(base)
    for email, default_user in default_users.items():
        if email not in existing_by_email:
            normalized_users.append(dict(default_user))
    if normalized_users:
        merged["users"] = normalized_users
    return merged


def load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        save_state(DEFAULT_STATE)
        return json.loads(json.dumps(DEFAULT_STATE))
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except JSONDecodeError:
        save_state(DEFAULT_STATE)
        return json.loads(json.dumps(DEFAULT_STATE))
    merged = _merge_defaults(state)
    if merged != state:
        save_state(merged)
    return merged


def save_state(state: Dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def list_users() -> List[Dict[str, Any]]:
    return load_state()["users"]


def get_user(email: str, password: str) -> Dict[str, Any] | None:
    state = load_state()
    for user in state["users"]:
        if user["email"].lower() == email.lower() and user["password"] == password:
            return user
    return None


def get_user_by_email(email: str) -> Dict[str, Any] | None:
    state = load_state()
    for user in state["users"]:
        if user["email"].lower() == email.lower():
            return user
    return None


def can_consume_credits(user: Dict[str, Any], cost: int) -> bool:
    if user["role"] == "admin":
        return True
    credits = user.get("credits")
    return isinstance(credits, int) and credits >= cost


def can_consume_tokens(user: Dict[str, Any], cost: int) -> bool:
    if user["role"] == "admin":
        return True
    balance = user.get("token_balance")
    return isinstance(balance, int) and balance >= cost


def consume_credits(email: str, cost: int) -> Dict[str, Any]:
    state = load_state()
    for user in state["users"]:
        if user["email"].lower() != email.lower():
            continue
        if user["role"] == "admin":
            return user
        if not can_consume_credits(user, cost):
            raise ValueError("Insufficient credits")
        user["credits"] -= cost
        save_state(state)
        return user
    raise ValueError("Unknown user")


def consume_tokens(email: str, cost: int) -> Dict[str, Any]:
    state = load_state()
    for user in state["users"]:
        if user["email"].lower() != email.lower():
            continue
        if user["role"] == "admin":
            return user
        if not can_consume_tokens(user, cost):
            raise ValueError("Insufficient tokens")
        user["token_balance"] -= cost
        save_state(state)
        return user
    raise ValueError("Unknown user")


def record_run(email: str, run_type: str, status: str, summary: str, cost: int, metadata: Dict[str, Any] | None = None) -> None:
    state = load_state()
    record = {
        "email": email,
        "run_type": run_type,
        "status": status,
        "summary": summary,
        "cost": cost,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if metadata:
        record.update(metadata)
    state["run_history"].insert(0, record)
    state["run_history"] = state["run_history"][:20]
    save_state(state)


def list_run_history() -> List[Dict[str, Any]]:
    return load_state()["run_history"]


def record_assistant_event(
    email: str,
    prompt: str,
    response: str,
    tokens_used: int,
    chart_points: List[Dict[str, Any]],
    provider: str = "local",
    model: str = "meghyan-analyst-local",
) -> None:
    state = load_state()
    state["assistant_history"].insert(
        0,
        {
            "email": email,
            "prompt": prompt,
            "response": response,
            "tokens_used": tokens_used,
            "chart_points": chart_points,
            "provider": provider,
            "model": model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    state["assistant_history"] = state["assistant_history"][:30]
    save_state(state)


def list_assistant_history(email: str | None = None) -> List[Dict[str, Any]]:
    history = load_state()["assistant_history"]
    if email is None:
        return history
    return [item for item in history if item["email"].lower() == email.lower()]


def _next_thread_id(threads: List[Dict[str, Any]]) -> str:
    return f"thr-{len(threads) + 1:04d}"


def create_assistant_thread(email: str, mode: str, title: str) -> Dict[str, Any]:
    state = load_state()
    thread = {
        "thread_id": _next_thread_id(state["assistant_threads"]),
        "email": email,
        "mode": mode,
        "title": title,
        "messages": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    state["assistant_threads"].insert(0, thread)
    save_state(state)
    return thread


def list_assistant_threads(email: str | None = None) -> List[Dict[str, Any]]:
    threads = load_state()["assistant_threads"]
    if email is None:
        return threads
    return [thread for thread in threads if thread["email"].lower() == email.lower()]


def get_assistant_thread(thread_id: str) -> Dict[str, Any] | None:
    for thread in load_state()["assistant_threads"]:
        if thread["thread_id"] == thread_id:
            return thread
    return None


def add_thread_message(
    thread_id: str,
    role: str,
    content: str,
    tokens_used: int = 0,
    provider: str = "local",
    model: str = "meghyan-analyst-local",
) -> Dict[str, Any]:
    state = load_state()
    for thread in state["assistant_threads"]:
        if thread["thread_id"] != thread_id:
            continue
        thread["messages"].append(
            {
                "role": role,
                "content": content,
                "tokens_used": tokens_used,
                "provider": provider,
                "model": model,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        thread["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        return thread
    raise ValueError("Unknown assistant thread")


def update_assistant_thread_mode(thread_id: str, mode: str) -> Dict[str, Any]:
    state = load_state()
    for thread in state["assistant_threads"]:
        if thread["thread_id"] != thread_id:
            continue
        thread["mode"] = mode
        thread["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        return thread
    raise ValueError("Unknown assistant thread")


def create_verification_request(email: str, company: str, model_name: str, scope: str, turnaround_days: int, token_cost: int) -> Dict[str, Any]:
    state = load_state()
    request_id = f"vrf-{len(state['verification_requests']) + 1:04d}"
    record = {
        "request_id": request_id,
        "email": email,
        "company": company,
        "model_name": model_name,
        "scope": scope,
        "status": "Queued",
        "turnaround_days": turnaround_days,
        "formal_output": "Formal verification package pending compute window.",
        "chart_link": f"/app/verification/{request_id}",
        "token_cost": token_cost,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    state["verification_requests"].insert(0, record)
    save_state(state)
    return record


def list_verification_requests(email: str | None = None) -> List[Dict[str, Any]]:
    requests = load_state()["verification_requests"]
    if email is None:
        return requests
    return [item for item in requests if item["email"].lower() == email.lower()]


def get_verification_request(request_id: str) -> Dict[str, Any] | None:
    for item in load_state()["verification_requests"]:
        if item["request_id"] == request_id:
            return item
    return None


def check_demo_rate_limit(ip: str, max_per_hour: int = 3) -> bool:
    now = datetime.now()
    cutoff = now - timedelta(hours=1)
    _rate_limits[ip] = [timestamp for timestamp in _rate_limits[ip] if timestamp > cutoff]
    if len(_rate_limits[ip]) >= max_per_hour:
        return False
    _rate_limits[ip].append(now)
    return True


def get_remaining_runs(ip: str, max_per_hour: int = 3) -> int:
    now = datetime.now()
    cutoff = now - timedelta(hours=1)
    recent = [timestamp for timestamp in _rate_limits[ip] if timestamp > cutoff]
    return max(0, max_per_hour - len(recent))


def reset_demo_rate_limit(ip_address: str) -> None:
    _rate_limits.pop(ip_address, None)
