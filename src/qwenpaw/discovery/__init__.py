# -*- coding: utf-8 -*-
"""Discovery agent package (layer 1 brain + AG-UI/A2UI seam).

Exporta:
- ``InterviewSession`` (camada 1): segura o ``DiscoveryState`` mutável e
  expõe as tools ``segment_lookup`` / ``reflect`` / ``emit_blueprint``.
- ``run_discovery_session`` / ``run_discovery_cli``: o loop de terminal do
  cérebro (Task 6) e seu wrapper de CLI.
- ``LiveDiscoverySession`` / ``make_live_session_factory``: a costura ao vivo
  que dirige o agente real um turno por vez pela Protocol de transporte.
- ``DiscoverySession`` + ``TurnResult`` (re-export da Protocol de transporte
  em ``session.py``, a costura canônica com o router AG-UI/A2UI).
"""

from .live_session import LiveDiscoverySession, make_live_session_factory
from .runner import run_discovery_cli, run_discovery_session
from .session import DiscoverySession, TurnResult
from .scripted_session import ScriptedDiscoverySession
from .tools import InterviewSession

__all__ = [
    "InterviewSession",
    "run_discovery_session",
    "run_discovery_cli",
    "LiveDiscoverySession",
    "ScriptedDiscoverySession",
    "make_live_session_factory",
    "DiscoverySession",
    "TurnResult",
]
