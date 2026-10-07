import json
import os
import random
import re
import time
from collections import Counter, defaultdict
from typing import Any

import httpx
import db


class AgentConfigurationError(RuntimeError):
    pass


class AgentResponseError(RuntimeError):
    pass


class AgentRateLimitError(AgentResponseError):
    def __init__(self, message: str, retry_after: int = 5):
        super().__init__(message)
        self.retry_after = retry_after


def classify_result(result: str) -> str:
    value = (result or "").strip().lower()
    if any(term in value for term in ("selected", "placed", "hired")):
        return "passed"
    if any(term in value for term in ("rejected", "failed", "fail")):
        return "failed"
    if "shortlist" in value or "qualified" in value:
        return "shortlisted"
    return "pending"


def sample_result_classification(result: str, sampler: random.SystemRandom) -> str:
    """Sample an interpretation of a result instead of treating labels as certain."""
    classification = classify_result(result)
    if classification == "failed":
        return sampler.choices(["failed", "pending", "passed"], weights=[0.75, 0.15, 0.10], k=1)[0]
    if classification in {"passed", "shortlisted"}:
        return sampler.choices(["passed", "shortlisted", "failed"], weights=[0.75, 0.15, 0.10], k=1)[0]
    return sampler.choices(["pending", "failed", "passed"], weights=[0.50, 0.25, 0.25], k=1)[0]


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def analyse_student_patterns(records: list[dict[str, Any]]) -> dict[str, Any]:
    sampler = random.SystemRandom()
    sampled_classifications = [sample_result_classification(record.get("result"), sampler) for record in records]
    total_rounds = len(records)
    passed = sum(classification in {"passed", "shortlisted"} for classification in sampled_classifications)
    failed_records = [record for record, classification in zip(records, sampled_classifications) if classification == "failed"]
    failed_by_round = Counter()
    weaknesses = Counter()
    rejection_reasons = Counter()
    scores = []

    for record in failed_records:
        round_name = record.get("round") or "Unknown round"
        failed_by_round[str(round_name)] += 1
        weakness = (record.get("weakness_area") or "Unspecified weakness").strip()
        weaknesses[weakness] += 1
        reason = (record.get("rejection_reason") or "Unspecified rejection reason").strip()
        rejection_reasons[reason] += 1

    for record, classification in zip(records, sampled_classifications):
        score = record.get("score")
        if score is not None and classification != "pending":
            try:
                scores.append(float(score))
            except (TypeError, ValueError):
                pass

    pass_rate = round((passed / total_rounds) * 100, 1) if total_rounds else 0.0

    # Build a Beta posterior. A failure on an easy drive is stronger evidence
    # than a failure on a drive where most candidates fail. Sampling the
    # posterior makes uncertainty visible instead of returning a fixed score.
    drive_failure_rates = db.get_drive_failure_rates(record.get("drive_id") for record in records)
    posterior_alpha = 2.0
    posterior_beta = 2.0
    for record, classification in zip(records, sampled_classifications):
        if classification not in {"failed", "passed", "shortlisted"}:
            continue
        drive_rate = min(max(drive_failure_rates.get(record.get("drive_id"), 0.5), 0.05), 0.95)
        if classification == "failed":
            posterior_alpha += 1.0 - drive_rate
            posterior_beta += drive_rate * 0.25
        else:
            posterior_beta += 1.0 - (drive_rate * 0.25)

    posterior_mean = posterior_alpha / (posterior_alpha + posterior_beta)
    samples = [sampler.betavariate(posterior_alpha, posterior_beta) for _ in range(256)]
    risk_probability = round(samples[-1], 3)
    risk_level = "high" if risk_probability >= 0.70 else "medium" if risk_probability >= 0.40 else "low"

    return {
        "total_rounds": total_rounds,
        "passed_rounds": passed,
        "failed_rounds": len(failed_records),
        "pass_rate": pass_rate,
        "risk_level": risk_level,
        "risk_probability": risk_probability,
        "risk_score": round(risk_probability * 100, 1),
        "risk_probability_mean": round(posterior_mean, 3),
        "risk_interval": [round(_percentile(samples, 0.1), 3), round(_percentile(samples, 0.9), 3)],
        "posterior": {"alpha": round(posterior_alpha, 3), "beta": round(posterior_beta, 3)},
        "drive_failure_rates": drive_failure_rates,
        "failed_by_round": dict(failed_by_round),
        "top_weaknesses": [
            {"area": area, "count": count} for area, count in weaknesses.most_common()
        ],
        "rejection_reasons": [
            {"reason": reason, "count": count}
            for reason, count in rejection_reasons.most_common()
        ],
        "score_average": round(sum(scores) / len(scores), 2) if scores else None,
        "records": records,
        "sampled_classifications": sampled_classifications,
    }


def compute_priority(patterns: dict[str, Any]) -> str:
    failures = patterns.get("failed_rounds", 0)
    risk = patterns.get("risk_level")
    if risk == "high" or failures >= 5:
        return "CRITICAL"
    if risk == "medium" or failures >= 2:
        return "HIGH"
    if failures == 1:
        return "MEDIUM"
    return "LOW"


def build_prompt(student: dict[str, Any], patterns: dict[str, Any], previous_actions: list[dict[str, Any]]) -> str:
    prompt_patterns = {
        key: value for key, value in patterns.items() if key != "records"
    }
    prompt_actions = [
        {
            key: action.get(key)
            for key in ("title", "weakness_area", "completed", "notes", "due_date")
            if action.get(key) is not None
        }
        for action in previous_actions[-6:]
    ]
    return f"""You are a placement intervention advisor. Analyze the student's verified placement data and propose practical, measurable support.

Student: {student.get('gmail')}
Department: {student.get('department') or 'Unknown'}
Failure analysis JSON:
{json.dumps(prompt_patterns, separators=(',', ':'), default=str)}

Previous intervention actions JSON:
{json.dumps(prompt_actions, separators=(',', ':'), default=str)}

Return only valid JSON with this shape:
{{
  "title": "short intervention title",
  "failure_summary": "concise evidence-based summary",
  "ai_analysis": "explanation of the most important pattern",
  "actions": [
    {{"title": "specific measurable action", "weakness_area": "area", "resources": "optional resources", "due_date": "optional ISO date"}}
  ]
}}
Do not invent scores or results that are not present in the analysis."""


def parse_agent_response(content: str) -> dict[str, Any]:
    cleaned = (content or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AgentResponseError("The agent returned invalid JSON") from exc
    if not isinstance(payload, dict) or not payload.get("title") or not isinstance(payload.get("actions"), list):
        raise AgentResponseError("The agent response is missing required intervention fields")
    return payload


def generate_agent_intervention(student: dict[str, Any], patterns: dict[str, Any], previous_actions: list[dict[str, Any]]) -> dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise AgentConfigurationError("GROQ_API_KEY is not configured")

    base_url = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1").rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"}
    configured_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    request_body = {
        "model": configured_model,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": build_prompt(student, patterns, previous_actions)}],
    }
    response = httpx.post(f"{base_url}/chat/completions", headers=headers, json=request_body, timeout=45.0)

    if response.status_code == 404:
        try:
            models_response = httpx.get(f"{base_url}/models", headers=headers, timeout=15.0)
            if models_response.is_success:
                model_ids = [item.get("id") for item in models_response.json().get("data", [])]
                preferred_models = [
                    configured_model,
                    "llama-3.3-70b-versatile",
                    "openai/gpt-oss-120b",
                    "llama-4-scout-17b-16e-instruct",
                ]
                replacement_model = next((model for model in preferred_models if model in model_ids), None)
                if replacement_model and replacement_model != configured_model:
                    request_body["model"] = replacement_model
                    response = httpx.post(f"{base_url}/chat/completions", headers=headers, json=request_body, timeout=45.0)
        except (httpx.HTTPError, ValueError, TypeError):
            pass

    if response.status_code == 429:
        retry_after_header = response.headers.get("Retry-After", "5")
        try:
            retry_after = max(1, min(int(float(retry_after_header)), 15))
        except (TypeError, ValueError):
            retry_after = 5
        for attempt in range(2):
            time.sleep(retry_after * (attempt + 1))
            response = httpx.post(f"{base_url}/chat/completions", headers=headers, json=request_body, timeout=45.0)
            if response.status_code != 429:
                break
        if response.status_code == 429:
            detail = response.text[:500].strip() or "Groq rate limit exceeded."
            raise AgentRateLimitError(f"Groq rate limit exceeded (HTTP 429): {detail}", retry_after)

    if response.is_error:
        detail = response.text[:500].strip() or "No provider error details were returned."
        raise AgentResponseError(f"Groq request failed with HTTP {response.status_code}: {detail}")
    body = response.json()
    choices = body.get("choices") or []
    if not choices or not choices[0].get("message", {}).get("content"):
        raise AgentResponseError("The agent returned an empty response")
    return parse_agent_response(choices[0]["message"]["content"])


def build_intervention(student: dict[str, Any], patterns: dict[str, Any], previous_actions: list[dict[str, Any]], created_by: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    generated = generate_agent_intervention(student, patterns, previous_actions)
    intervention = {
        "student_id": student["uuid"],
        "student_gmail": student["gmail"],
        "title": generated["title"].strip(),
        "failure_summary": generated.get("failure_summary", "").strip(),
        "ai_analysis": generated.get("ai_analysis", "").strip(),
        "priority": compute_priority(patterns),
        "status": "OPEN",
        "created_by": created_by,
    }
    actions = [
        {
            "title": str(action.get("title", "")).strip(),
            "weakness_area": action.get("weakness_area"),
            "resources": action.get("resources"),
            "due_date": action.get("due_date"),
        }
        for action in generated["actions"]
        if str(action.get("title", "")).strip()
    ]
    if not actions:
        raise AgentResponseError("The agent returned no usable actions")
    return intervention, actions
