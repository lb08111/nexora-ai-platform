# -*- coding: utf-8 -*-
"""Meeting facilitation tool for the Jotaduo Orchestrator.

Exposes ``convene_meeting`` — the orchestrator broadcasts a topic to
several specialists in parallel and aggregates their answers into a
single transcript. Used when the case is complex enough that a single
hand-off via ``chat_with_agent`` would lose context.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from jotaduo.agents.br_team.tools._utils import json_response, text_response

from ..constants import AGENT_ROLE_MAP, ALL_AGENT_IDS
from ..store import Contribution, get_meeting_store

__all__ = ["convene_meeting"]


async def convene_meeting(
    topic: str,
    participants: list[str] | None = None,
    convener: str = "jotaduo-orchestrator",
    context: str = "",
    per_agent_timeout_s: float = 30.0,
):
    """Convene a meeting with N specialists in parallel.

    Args:
        topic: The question or scenario the team should weigh in on.
            Keep it self-contained — each agent receives only this
            text plus the shared ``context``.
        participants: List of Jotaduo agent IDs to invite. Defaults to
            all registered Jotaduo specialists (excluding the convener).
            Accepts also bare role names ("vendas", "atendente").
        convener: Agent ID of who is convening (informational).
        context: Free-form shared briefing prepended to each prompt.
        per_agent_timeout_s: Hard ceiling per agent.

    Returns:
        ToolResponse with a JSON payload describing the meeting:
        ``{meeting_id, transcript: [...], summary, finished_at}``.
    """
    if not topic or not topic.strip():
        return text_response(
            "❌ Tópico vazio. Diga sobre o que a reunião é.",
        )

    invitees = _resolve_participants(participants, convener)
    if not invitees:
        return text_response(
            "❌ Nenhum participante válido. IDs aceitos: "
            + ", ".join(ALL_AGENT_IDS),
        )

    store = get_meeting_store()
    meeting = store.create(
        topic=topic.strip(),
        convener=convener,
        participants=invitees,
        context={"briefing": context} if context else {},
    )

    prompt = _build_prompt(topic, context)
    tasks = [
        _ask_one(agent_id, prompt, per_agent_timeout_s)
        for agent_id in invitees
    ]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    for contrib in results:
        store.add_contribution(meeting.id, contrib)

    summary = _summarize(meeting.topic, results)
    store.finish(meeting.id, summary=summary, status="completed")

    payload = {
        "meeting_id": meeting.id,
        "topic": meeting.topic,
        "participants": invitees,
        "transcript": [
            {
                "agent_id": c.agent_id,
                "agent_name": c.agent_name,
                "role": c.role,
                "content": c.content,
                "elapsed_ms": c.elapsed_ms,
                "error": c.error,
            }
            for c in results
        ],
        "summary": summary,
        "finished_at": meeting.finished_at,
    }
    return json_response(payload)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _resolve_participants(
    raw: list[str] | None,
    convener: str,
) -> list[str]:
    """Accept agent IDs or bare role names. Drop the convener."""
    if not raw:
        candidates = list(ALL_AGENT_IDS)
    else:
        candidates = []
        role_to_id = {v: k for k, v in AGENT_ROLE_MAP.items()}
        for item in raw:
            if item in ALL_AGENT_IDS:
                candidates.append(item)
            elif item in role_to_id:
                candidates.append(role_to_id[item])
    # de-dup preserving order, drop convener
    seen: set[str] = set()
    out: list[str] = []
    for cand in candidates:
        if cand == convener or cand in seen:
            continue
        seen.add(cand)
        out.append(cand)
    return out


def _build_prompt(topic: str, context: str) -> str:
    parts = [
        "Você foi convocado para uma reunião do time Jotaduo.",
        f"Tópico: {topic.strip()}",
    ]
    if context.strip():
        parts.append(f"Contexto compartilhado: {context.strip()}")
    parts.append(
        "Responda em no máximo 6 frases, focando no que VOCÊ "
        "(no seu papel) recomenda. Seja objetivo.",
    )
    return "\n\n".join(parts)


async def _ask_one(
    agent_id: str,
    prompt: str,
    timeout_s: float,
) -> Contribution:
    start = time.monotonic()
    role = AGENT_ROLE_MAP.get(agent_id, "unknown")
    try:
        content = await asyncio.wait_for(
            _call_agent(agent_id, prompt),
            timeout=timeout_s,
        )
        return Contribution(
            agent_id=agent_id,
            agent_name=agent_id,
            role=role,
            content=content,
            elapsed_ms=int((time.monotonic() - start) * 1000),
        )
    except asyncio.TimeoutError:
        return Contribution(
            agent_id=agent_id,
            agent_name=agent_id,
            role=role,
            content="",
            elapsed_ms=int((time.monotonic() - start) * 1000),
            error=f"timeout após {timeout_s:.0f}s",
        )
    except Exception as exc:  # pylint: disable=broad-except
        return Contribution(
            agent_id=agent_id,
            agent_name=agent_id,
            role=role,
            content="",
            elapsed_ms=int((time.monotonic() - start) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )


async def _call_agent(agent_id: str, prompt: str) -> str:
    """Delegate to JotaDuo's native ``chat_with_agent`` tool.

    Falls back to a stub response (useful in tests) when the platform
    coordinator is not available.
    """
    try:
        from jotaduo.agents.tools.agent_management import chat_with_agent
    except ImportError:
        return _stub_response(agent_id, prompt)

    try:
        resp = await chat_with_agent(agent_id=agent_id, message=prompt)
    except Exception as exc:  # pylint: disable=broad-except
        raise RuntimeError(f"chat_with_agent failed: {exc}") from exc

    return _extract_text(resp)


def _extract_text(resp: Any) -> str:
    if resp is None:
        return ""
    if isinstance(resp, str):
        return resp
    content = getattr(resp, "content", resp)
    if isinstance(content, list):
        chunks: list[str] = []
        for blk in content:
            if isinstance(blk, dict):
                txt = blk.get("text") or blk.get("content") or ""
            else:
                txt = getattr(blk, "text", None) or str(blk)
            if txt:
                chunks.append(str(txt))
        return "\n".join(chunks).strip()
    if isinstance(content, dict):
        return content.get("text") or json.dumps(content, ensure_ascii=False)
    return str(content)


def _stub_response(agent_id: str, prompt: str) -> str:
    """Deterministic stub for offline/testing scenarios."""
    role = AGENT_ROLE_MAP.get(agent_id, "unknown")
    excerpt = prompt[:80].replace("\n", " ")
    return (
        f"[stub:{role}] reconheci o tópico '{excerpt}…' "
        "e ofereço minha opinião baseada no meu papel."
    )


def _summarize(topic: str, contribs: list[Contribution]) -> str:
    ok = [c for c in contribs if not c.error]
    err = [c for c in contribs if c.error]
    head = f"Reunião sobre: {topic}\n"
    head += f"{len(ok)} contribuição(ões), {len(err)} sem resposta."
    if not ok:
        return head
    lines = [head, ""]
    for c in ok:
        first_line = c.content.split("\n", 1)[0].strip()
        if len(first_line) > 160:
            first_line = first_line[:157] + "…"
        lines.append(f"• {c.role}: {first_line}")
    return "\n".join(lines)
