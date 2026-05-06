from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path
from typing import Any, Dict, List
from urllib import error, request

ROOT = Path(__file__).resolve().parent.parent


def _load_local_env() -> None:
    # .env.local takes precedence over .env — check it first
    for candidate in (ROOT / ".env.local", ROOT / ".env", ROOT / "meghyan_portal" / ".env"):
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
        break


_load_local_env()


def llm_config() -> Dict[str, str]:
    return {
        "mode": os.getenv("MEGHYAN_LLM_MODE", "local"),
        "endpoint": os.getenv("MEGHYAN_LLM_ENDPOINT", "").rstrip("/"),
        "api_key": os.getenv("MEGHYAN_LLM_API_KEY", ""),
        "model": os.getenv("MEGHYAN_LLM_MODEL", "meghyan-analyst-local"),
    }


def llm_status() -> Dict[str, Any]:
    config = llm_config()
    if config["mode"] == "openai_compatible":
        provider_ready = bool(config["endpoint"] and config["api_key"])
    elif config["mode"] == "anthropic":
        provider_ready = bool(config["api_key"])
    else:
        provider_ready = True
    return {
        "mode": config["mode"],
        "model": config["model"],
        "provider_ready": provider_ready,
    }


def compact_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    comparison_summary = metrics.get("comparison", {}).get("summary", {})
    tree_summary = metrics.get("quantum_tree", {}).get("summary", {})
    latest_run = metrics.get("latest_run", {}) or {}
    quantum_tree = metrics.get("quantum_tree", {}) or {}
    latest_top_failures = latest_run.get("top_failures") or quantum_tree.get("top_failures", [])[:3]
    latest_risk_score = latest_run.get("risk_score", metrics.get("latest_tree_risk", "n/a"))
    latest_failures_found = latest_run.get("failures_found", quantum_tree.get("failures_found", 0))
    latest_scenario = latest_run.get("scenario_type", quantum_tree.get("scenario_type", "unknown"))
    return {
        "benchmark": {
            "winner": metrics.get("comparison", {}).get("winner", "Unknown"),
            "qaoa_unique_failures": comparison_summary.get("qaoa_unique_failures", 0),
            "mc_unique_failures": comparison_summary.get("mc_unique_failures", 0),
            "qaoa_first_failure": comparison_summary.get("qaoa_time_to_first_failure", "n/a"),
            "mc_first_failure": comparison_summary.get("mc_time_to_first_failure", "n/a"),
        },
        "quantum_tree": {
            "teacher_accuracy": tree_summary.get("teacher_accuracy", "n/a"),
            "teacher_loss": tree_summary.get("teacher_loss", "n/a"),
            "quantum_backend": tree_summary.get("quantum_backend", "n/a"),
            "mean_quantum_score": tree_summary.get("mean_quantum_score", "n/a"),
            "mean_student_score": tree_summary.get("mean_student_score", "n/a"),
            "student_mse": tree_summary.get("student_mse", "n/a"),
        },
        "latest_run": {
            "scenario_type": latest_scenario,
            "risk_score": latest_risk_score,
            "failures_found": latest_failures_found,
            "top_failures": latest_top_failures,
        },
    }


def build_messages(prompt: str, metrics: Dict[str, Any], mode: str = "internal", history: List[Dict[str, Any]] | None = None) -> List[Dict[str, str]]:
    compact = compact_metrics(metrics)
    history = history or []
    mode_instruction = (
        "Internal mode: optimize for candid technical diagnosis, modeling critique, and next-step experimentation."
        if mode == "internal"
        else "Customer report mode: optimize for polished, client-safe language, executive clarity, and decision-ready recommendations without exposing unnecessary internal uncertainty."
    )
    system = (
        "You are Meghyan Analyst, an enterprise assurance model assistant for the MeghyanAI platform. "
        "You analyze Quantum Tree, Qiskit benchmark, and formal verification workflow outputs. "
        "Be concise, technically grounded, honest about uncertainty, and product-aware. "
        "Do not claim quantum advantage unless the supplied metrics support it. "
        "If Monte Carlo is ahead, say so clearly and explain why Quantum Tree can still be valuable as a hybrid refinement workflow. "
        "Structure responses in short paragraphs. Include implications for enterprise usage when relevant. "
        f"{mode_instruction}"
    )
    context = "Live platform context:\n" + json.dumps(compact, indent=2)
    messages = [{"role": "system", "content": system}, {"role": "system", "content": context}]
    for item in history[-4:]:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": str(content)})
        else:
            if item.get("prompt"):
                messages.append({"role": "user", "content": str(item.get("prompt", ""))})
            if item.get("response"):
                messages.append({"role": "assistant", "content": str(item.get("response", ""))})
    messages.append({"role": "user", "content": prompt})
    return messages


def _post_openai_compatible(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    config = llm_config()
    if not config["endpoint"] or not config["api_key"]:
        raise RuntimeError("OpenAI-compatible LLM mode is enabled, but endpoint or API key is missing.")

    body = json.dumps(
        {
            "model": config["model"],
            "messages": messages,
            "temperature": 0.3,
        }
    ).encode("utf-8")
    req = request.Request(
        url=f"{config['endpoint']}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"LLM provider error: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"LLM provider unavailable: {exc.reason}") from exc

    content = payload["choices"][0]["message"]["content"]
    usage = payload.get("usage", {})
    return {
        "answer": content,
        "provider": "openai_compatible",
        "model": config["model"],
        "usage_tokens": usage.get("total_tokens"),
    }


def _post_anthropic(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    config = llm_config()
    if not config["api_key"]:
        raise RuntimeError("Anthropic mode is enabled but MEGHYAN_LLM_API_KEY is missing.")

    # Anthropic API separates system messages from the conversation
    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    conversation = [m for m in messages if m["role"] != "system"]
    system_text = "\n\n".join(system_parts)
    model = config["model"] or "claude-haiku-4-5-20251001"

    body = json.dumps(
        {
            "model": model,
            "max_tokens": 1024,
            "system": system_text,
            "messages": conversation,
        }
    ).encode("utf-8")
    req = request.Request(
        url="https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": config["api_key"],
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Anthropic API error: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Anthropic API unavailable: {exc.reason}") from exc

    content = payload["content"][0]["text"]
    usage = payload.get("usage", {})
    return {
        "answer": content,
        "provider": "anthropic",
        "model": model,
        "usage_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
    }


def _latest_assistant_message(history: List[Dict[str, Any]] | None) -> str:
    if not history:
        return ""
    for item in reversed(history):
        if item.get("role") == "assistant" and item.get("content"):
            return str(item["content"])
    return ""


def _intent_labels(normalized: str) -> List[str]:
    intents: List[str] = []
    if any(word in normalized for word in ["why", "ahead", "better", "beat", "winner"]):
        intents.append("benchmark")
    if any(word in normalized for word in ["verify", "verification", "formal", "audit", "certification"]):
        intents.append("verification")
    if any(word in normalized for word in ["price", "pricing", "token", "charge", "monetize", "billing"]):
        intents.append("pricing")
    if any(word in normalized for word in ["customer", "client", "external", "report", "rewrite"]):
        intents.append("customer")
    if any(word in normalized for word in ["roadmap", "next", "improve", "fix", "plan"]):
        intents.append("roadmap")
    if not intents:
        intents.append("general")
    return intents


def _local_reasoner(prompt: str, metrics: Dict[str, Any], mode: str, history: List[Dict[str, Any]] | None) -> Dict[str, Any]:
    compact = compact_metrics(metrics)
    benchmark = compact["benchmark"]
    tree = compact["quantum_tree"]
    latest_run = compact["latest_run"]
    normalized = prompt.strip().lower()
    intents = _intent_labels(normalized)
    previous_assistant = _latest_assistant_message(history)
    top_failure = {}
    if latest_run.get("top_failures"):
        top_failure = latest_run["top_failures"][0]
    top_type = str(top_failure.get("type", "unranked scenario")).replace("_", " ")
    top_desc = str(top_failure.get("description", "No top-failure description available."))
    risk_score = latest_run.get("risk_score", "n/a")
    scenario_type = latest_run.get("scenario_type", "unknown")

    observed = (
        f"Current posture: the latest run is a {scenario_type} review with a risk score of {risk_score}. "
        f"The highest-ranked issue is {top_type}. Quantum Tree is running on {tree['quantum_backend']} with teacher accuracy {tree['teacher_accuracy']} and student MSE {tree['student_mse']}."
    )

    if any(word in normalized for word in ["highest", "top issue", "biggest", "worst", "risk scenario"]):
        answer = (
            f"The highest-risk scenario in the current run is {top_type}. {top_desc}\n\n"
            f"This matters because the latest run is already scoring at {risk_score}, which means the model is not just showing noise or edge jitter. "
            f"It is surfacing a failure pattern your team should treat as a real pre-deployment issue.\n\n"
            f"The next move is to reproduce this scenario, review the policy decision at the conflict point, and then generate nearby variants to confirm whether the failure is isolated or systematic."
        )
    elif "customer" in intents or mode == "customer":
        answer = (
            f"Here is the customer-safe summary: MeghyanAI reviewed the current {scenario_type} model and found a meaningful risk pattern that should be addressed before broader deployment. "
            f"The main issue today is {top_type}.\n\n"
            f"The platform is useful here because it does not stop at a score. It identifies the failure case, ranks it, and turns it into something the engineering team can act on.\n\n"
            f"Recommended next step: share the summary with the customer now, then open a formal verification request if they need a longer evidence package or audit-ready documentation."
        )
    elif "verification" in intents:
        answer = (
            f"The formal verification path should start from the current top issue: {top_type}. {top_desc}\n\n"
            "For the short-term product surface, the right output is a ranked hazard summary, supporting scenarios, and a clear explanation of impact. "
            "For the formal path, the 5 to 10 day workflow should package reproducibility notes, decision traces, and the final report artifact.\n\n"
            "That separation keeps the product fast for normal users while preserving a serious review path for customers who need compliance-grade output."
        )
    elif "pricing" in intents:
        answer = (
            "The cleanest pricing split is to charge lightly for analysis and more heavily for compute-heavy runs.\n\n"
            "Use analyst tokens for question answering, summaries, and rewrites. Use credits for full assurance runs, scenario generation, and verification packaging.\n\n"
            "That lets customers explore results cheaply while preserving margin on the workflows that actually consume the expensive model and simulation stack."
        )
    elif "roadmap" in intents or any(word in normalized for word in ["fix first", "what should", "improve", "next step"]):
        answer = (
            f"The first thing to fix is the behavior behind {top_type}. {top_desc}\n\n"
            "Do not treat the latest benchmark as a marketing claim yet. Treat it as a prioritization signal: fix the highest-ranked issue, rerun the same scenario family, and watch whether the risk score falls.\n\n"
            f"After that, the next product improvement is to generate neighboring scenarios around the same failure so the ML team can retrain against a whole cluster, not just one example."
        )
    elif "benchmark" in intents:
        answer = (
            f"The benchmark still favors {benchmark['winner']}. QAOA surfaced {benchmark['qaoa_unique_failures']} failures while Monte Carlo surfaced {benchmark['mc_unique_failures']}.\n\n"
            "That does not make the product invalid. It means the direct-search benchmark is still easier for the classical baseline than for the current quantum formulation.\n\n"
            "The stronger product story is the hybrid one: use Quantum Tree to prioritize rare scenarios, then use the student and analyst layers to turn those findings into something operational."
        )
    else:
        answer = (
            f"The current run says the model still needs work. The clearest issue right now is {top_type}. {top_desc}\n\n"
            "MeghyanAI is most useful when it turns that raw result into a decision: what failed, why it matters, and what the team should do next.\n\n"
            "If you want, ask for a customer-safe summary, the engineering next step, or a verification plan and I will reshape the answer around that goal."
        )

    if previous_assistant and any(word in normalized for word in ["rewrite", "rephrase", "turn that into"]):
        answer += "\n\nI treated this as a rewrite of the previous answer, so the focus is on changing the framing without changing the underlying findings."

    answer = "\n\n".join(textwrap.fill(paragraph, width=108) for paragraph in answer.split("\n\n") if paragraph)
    return {
        "answer": answer,
        "provider": "local",
        "model": "meghyan-analyst-local",
        "usage_tokens": None,
    }


def generate_llm_response(prompt: str, metrics: Dict[str, Any], mode: str = "internal", history: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    messages = build_messages(prompt, metrics, mode, history)
    config = llm_config()
    if config["mode"] == "anthropic":
        return _post_anthropic(messages)
    if config["mode"] == "openai_compatible":
        return _post_openai_compatible(messages)
    return _local_reasoner(prompt, metrics, mode, history)
