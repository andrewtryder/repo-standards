"""Optional advisory AI classification for ambiguous workflows."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .cicd import UNKNOWN_REVIEW_REQUIRED


AI_API_URL = "https://models.github.ai/inference/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"


def available_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def classify_workflow_summary(
    summary: dict[str, Any],
    *,
    model: str = DEFAULT_MODEL,
    timeout: float = 20.0,
) -> dict[str, Any] | None:
    token = available_token()
    if not token:
        return None
    system = (
        "Classify a GitHub Actions workflow for a repo-standards migration. "
        "Return JSON with classification, confidence, reason, and recommended_action. "
        "Use KEEP_DEPLOY, KEEP_RELEASE, or UNKNOWN_REVIEW_REQUIRED unless the summary "
        "is clearly a duplicate standards check."
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(summary, sort_keys=True)},
        ],
        "temperature": 0.1,
        "max_tokens": 600,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        AI_API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError):
        return None
    if not isinstance(result, dict):
        return None
    result.setdefault("classification", UNKNOWN_REVIEW_REQUIRED)
    result.setdefault("confidence", 0)
    result.setdefault("recommended_action", "review")
    return result

