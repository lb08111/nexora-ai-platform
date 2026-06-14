# -*- coding: utf-8 -*-
"""Taxonomia híbrida de segmento: trilhos curados (CNAE) + fallback p/ LLM."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

_DATA = Path(__file__).parent / "data" / "cnae_seed.json"


class SegmentInfo(BaseModel):
    key: str
    label: str
    cnae: str = ""
    keywords: list[str] = []
    typical_areas: list[str] = []
    typical_processes: list[str] = []
    common_pains: list[str] = []
    common_integrations: list[str] = []


@lru_cache(maxsize=1)
def load_segments() -> tuple[SegmentInfo, ...]:
    raw = json.loads(_DATA.read_text(encoding="utf-8"))
    return tuple(SegmentInfo.model_validate(item) for item in raw)


def lookup_segment(query: str) -> SegmentInfo | None:
    """Casa o texto do empresário com um segmento da seed por palavra-chave.

    Retorna None quando nenhum trilho casa (cai no raciocínio livre do LLM).
    """
    q = (query or "").lower()
    best: SegmentInfo | None = None
    best_hits = 0
    for seg in load_segments():
        hits = sum(1 for kw in seg.keywords if kw.lower() in q)
        if hits > best_hits:
            best, best_hits = seg, hits
    return best if best_hits > 0 else None
