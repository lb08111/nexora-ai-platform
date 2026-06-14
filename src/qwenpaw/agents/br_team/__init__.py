# -*- coding: utf-8 -*-
"""Time de sub-agentes especialistas para empresas brasileiras.

Este pacote materializa o `TeamBlueprint` produzido pelo
`qwenpaw.discovery.DiscoveryAgent` em agentes ReAct concretos prontos
para atender os segmentos cobertos pela taxonomia (e-commerce, varejo,
serviços, alimentação/delivery, saúde, educação, beleza).

API pública:
- `NexoraOrchestrator`: orquestrador que delega para os especialistas.
- `build_team_from_blueprint`: mapeia o blueprint do discovery em agentes.
- `SPECIALIST_REGISTRY`: dicionário ``role`` -> factory de especialista.
"""

from __future__ import annotations

from .factory import (
    SPECIALIST_REGISTRY,
    SpecialistFactory,
    build_team_from_blueprint,
)

__all__ = [
    "NexoraOrchestrator",
    "SPECIALIST_REGISTRY",
    "SpecialistFactory",
    "build_team_from_blueprint",
]


def __getattr__(name: str):
    """Lazy load do orquestrador para evitar import pesado de agentscope."""
    if name == "NexoraOrchestrator":
        from .orchestrator import NexoraOrchestrator

        return NexoraOrchestrator
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}",
    )
