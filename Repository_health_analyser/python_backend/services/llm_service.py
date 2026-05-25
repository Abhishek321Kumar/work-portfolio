"""
llm_service.py — Cost-justified LLM integration for architectural insights.

Per the project constraints, LLM calls are made in exactly three cases:

  Call 1 — Spike Explainer (triggered per anomaly, not per commit):
    When a commit's complexity spikes > 25%, send the diff to the LLM and ask:
    "What structural decision caused this spike, and is it intentional?"
    Fired at most once per spike commit. On a 500-commit repo: ~8–12 calls total.

  Call 2 — Architectural Drift Summary (triggered every 50 commits or at tags):
    Send the compacted graph delta (not raw code) to the LLM.
    Generate a 3-sentence human-readable summary of what changed architecturally.
    Input is small (JSON delta), output is high-value prose.

  Call 3 — Demo Narrative (one-time per repo):
    A single call that generates a written walkthrough of the repo's health story.
    E.g. "Between commits 100–300, coupling tripled in the auth module..."
    This is a demo asset, not a recurring cost.

Libraries:
  - openai  : Official OpenAI Python SDK (pip install openai)
              Uses gpt-4o-mini for cost efficiency — smart enough for code analysis.
  - httpx   : HTTP client used by the openai SDK under the hood

Environment variables:
  OPENAI_API_KEY : Required for LLM calls. If absent, returns a placeholder message.

Caching strategy:
  All LLM responses are cached in the `llm_cache` SQLite table (keyed by
  repo_id + sha + kind). This ensures:
  - Zero duplicate API calls for the same commit across page refreshes
  - Instant responses after the first call
  - Cost remains bounded even if the user reloads the insights page repeatedly
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenAI client setup
# ---------------------------------------------------------------------------

_client = None


def _get_client():
    """
    Lazily initialise the OpenAI client.
    Returns None if OPENAI_API_KEY is not set, which disables LLM calls.
    """
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning(
            "OPENAI_API_KEY not set — LLM calls disabled. "
            "Set the env var to enable spike explanations and architectural summaries."
        )
        return None

    try:
        from openai import OpenAI
        _client = OpenAI(api_key=api_key)
        return _client
    except ImportError:
        logger.error("openai package not installed. Run: pip install openai")
        return None


def _call_llm(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 600,
) -> Optional[str]:
    """
    Make a single LLM API call using gpt-4o-mini.

    Args:
        system_prompt : Sets the LLM role and output format
        user_message  : The specific analysis request with data
        max_tokens    : Response length cap (keep short for cost control)

    Returns:
        Response text, or None if the call fails or API key is missing.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Call 1: Spike Explainer
# ---------------------------------------------------------------------------

SPIKE_SYSTEM_PROMPT = """You are an expert software architect analysing a Git commit.
You will be given a code diff and metrics showing a significant complexity spike.
Your task:
1. Identify WHAT structural decision caused the spike (new abstraction, big function, deep nesting, etc.)
2. State whether this looks INTENTIONAL (e.g. a new feature) or ACCIDENTAL (e.g. poor refactoring)
3. Give 2-3 concrete, actionable recommendations if the spike looks problematic

Keep your response concise and technical. Output JSON with these exact keys:
{
  "explanation": "1-2 sentence summary of what happened",
  "is_intentional": true/false,
  "recommendations": ["action 1", "action 2"]
}"""


def generate_spike_explanation(
    sha: str,
    complexity_before: Optional[float],
    complexity_after: Optional[float],
    diff_text: str,
    changed_files: List[str],
) -> Dict[str, Any]:
    """
    Generate an LLM explanation for a complexity spike.

    This is Call 1 in the constraint document. Fired only when
    metrics_engine.is_spike_commit() returns True.

    Args:
        sha               : Commit hash (for context)
        complexity_before : Mean complexity at parent commit
        complexity_after  : Mean complexity at this commit
        diff_text         : Git diff text (truncated to fit context window)
        changed_files     : List of files modified in this commit

    Returns:
        Dict with keys: explanation, is_intentional, recommendations
    """
    pct_change = 0.0
    if complexity_before and complexity_before > 0:
        pct_change = ((complexity_after or 0) - complexity_before) / complexity_before * 100

    # Truncate diff to prevent context overflow (keep under 2000 chars)
    diff_preview = diff_text[:2000] if diff_text else "(diff not available)"

    user_message = f"""Commit: {sha[:8]}
Complexity before: {complexity_before:.1f if complexity_before else 'N/A'}
Complexity after:  {complexity_after:.1f if complexity_after else 'N/A'}
Change: +{pct_change:.1f}%
Files changed: {', '.join(changed_files[:5])}

Diff preview:
{diff_preview}"""

    response_text = _call_llm(SPIKE_SYSTEM_PROMPT, user_message, max_tokens=400)

    if response_text:
        try:
            # Strip markdown code fences if present
            text = response_text.strip()
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:-1])
            data = json.loads(text)
            return {
                "explanation": data.get("explanation", response_text),
                "is_intentional": data.get("is_intentional"),
                "recommendations": data.get("recommendations", []),
            }
        except json.JSONDecodeError:
            # Return plain text if JSON parsing fails
            return {
                "explanation": response_text,
                "is_intentional": None,
                "recommendations": [],
            }

    # Fallback when API key is missing or call fails
    return {
        "explanation": (
            f"This commit increased cyclomatic complexity by {pct_change:.1f}%. "
            f"Set OPENAI_API_KEY to get a detailed structural analysis."
        ),
        "is_intentional": None,
        "recommendations": [
            "Review the changed functions for excessive branching or nesting.",
            "Consider breaking large functions into smaller, focused units.",
        ],
    }


# ---------------------------------------------------------------------------
# Call 2: Architectural Drift Summary
# ---------------------------------------------------------------------------

ARCH_SYSTEM_PROMPT = """You are a principal software architect reviewing a codebase's structural evolution.
You will be given a compact JSON summary of how a repository's dependency graph changed over time.
Write a 3-sentence architectural summary that a senior engineer would find immediately useful.
Focus on: what changed structurally, which modules are gaining/losing connections, and what this means for maintainability.
Output JSON:
{
  "summary": "3-sentence architectural summary",
  "key_trends": ["trend 1", "trend 2", "trend 3"],
  "risk_modules": ["module that needs attention", ...]
}"""


def generate_architectural_summary(
    repo_name: str,
    total_commits: int,
    spike_count: int,
    top_hotspots: List[Dict],
    avg_complexity_trend: List[float],
) -> Dict[str, Any]:
    """
    Generate an architectural drift summary for a repository.

    This is Call 2 in the constraint document. Called once per repo when
    all commits have been processed (or every 50 commits in a live system).

    Args:
        repo_name            : Repository name (for context)
        total_commits        : Total commits analysed
        spike_count          : Number of complexity spikes detected
        top_hotspots         : Top 5 hotspot files with risk scores
        avg_complexity_trend : List of average complexity values over commit history

    Returns:
        Dict with keys: summary, key_trends, risk_modules
    """
    hotspot_summary = [
        {"file": h["file_path"], "risk": h["risk_score"], "churn": h["churn_count"]}
        for h in top_hotspots[:5]
    ]

    # Sample complexity trend at 10 evenly spaced points
    n = len(avg_complexity_trend)
    if n > 10:
        step = n // 10
        sampled = [avg_complexity_trend[i] for i in range(0, n, step)][:10]
    else:
        sampled = avg_complexity_trend

    user_message = f"""Repository: {repo_name}
Total commits analysed: {total_commits}
Complexity spikes detected: {spike_count}

Complexity trend (sampled): {[round(x, 1) for x in sampled]}

Top hotspot files:
{json.dumps(hotspot_summary, indent=2)}"""

    response_text = _call_llm(ARCH_SYSTEM_PROMPT, user_message, max_tokens=500)

    if response_text:
        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:-1])
            data = json.loads(text)
            return {
                "summary": data.get("summary", response_text),
                "key_trends": data.get("key_trends", []),
                "risk_modules": data.get("risk_modules", []),
            }
        except json.JSONDecodeError:
            return {
                "summary": response_text,
                "key_trends": [],
                "risk_modules": [],
            }

    # Fallback
    return {
        "summary": (
            f"{repo_name} shows {spike_count} complexity spikes across {total_commits} commits. "
            f"Set OPENAI_API_KEY for AI-powered architectural analysis."
        ),
        "key_trends": [
            f"{spike_count} complexity spikes detected",
            f"{len(top_hotspots)} high-risk files identified",
        ],
        "risk_modules": [h["file_path"] for h in top_hotspots[:3]],
    }


# ---------------------------------------------------------------------------
# Call 3: Demo Narrative
# ---------------------------------------------------------------------------

NARRATIVE_SYSTEM_PROMPT = """You are a principal engineer writing an executive summary of a codebase's health evolution.
You will receive metrics about a repository's complexity and coupling trends over time.
Write a compelling, technical narrative (4-6 sentences) that tells the "story" of this codebase.
Identify the turning points, the riskiest periods, and the current architectural state.
Output JSON:
{
  "narrative": "4-6 sentence narrative",
  "highlights": ["key finding 1", "key finding 2", "key finding 3", "key finding 4"]
}"""


def generate_repo_narrative(
    repo_name: str,
    total_commits: int,
    spike_commits: List[Dict],
    peak_complexity_commit: Optional[Dict],
    current_avg_complexity: float,
    top_risky_files: List[str],
) -> Dict[str, Any]:
    """
    Generate a one-time demo narrative for the repository health story.

    This is Call 3 in the constraint document. Called once per repo at the
    end of ingestion. The result is cached permanently in SQLite.

    Args:
        repo_name                : Repository display name
        total_commits            : Total commits analysed
        spike_commits            : List of spike commit summaries (sha, message, delta)
        peak_complexity_commit   : The commit with highest complexity spike
        current_avg_complexity   : Complexity at the most recent commit
        top_risky_files          : Top 3 riskiest file paths

    Returns:
        Dict with keys: narrative, highlights
    """
    spike_summary = [
        f"commit {s['sha'][:8]}: {s['message'][:50]}"
        for s in spike_commits[:5]
    ]

    user_message = f"""Repository: {repo_name}
Total commits: {total_commits}
Current average complexity: {current_avg_complexity:.1f}

Complexity spike commits ({len(spike_commits)} total):
{chr(10).join(spike_summary) if spike_summary else 'None detected'}

Peak spike: {peak_complexity_commit['sha'][:8] if peak_complexity_commit else 'N/A'}

Top risky files: {', '.join(top_risky_files[:3])}"""

    response_text = _call_llm(NARRATIVE_SYSTEM_PROMPT, user_message, max_tokens=600)

    if response_text:
        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:-1])
            data = json.loads(text)
            return {
                "narrative": data.get("narrative", response_text),
                "highlights": data.get("highlights", []),
            }
        except json.JSONDecodeError:
            return {
                "narrative": response_text,
                "highlights": [],
            }

    # Fallback
    return {
        "narrative": (
            f"{repo_name} has been analysed across {total_commits} commits. "
            f"{len(spike_commits)} complexity spikes were detected. "
            f"Set OPENAI_API_KEY for a detailed AI-powered health narrative."
        ),
        "highlights": [
            f"{total_commits} commits analysed",
            f"{len(spike_commits)} complexity spikes",
            f"Current mean complexity: {current_avg_complexity:.1f}",
        ],
    }
