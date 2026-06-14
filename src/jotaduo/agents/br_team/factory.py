# -*- coding: utf-8 -*-
"""Factory que mapeia o ``TeamBlueprint`` do discovery em sub-agentes.

O ``DiscoveryAgent`` produz um ``TeamBlueprint`` com uma lista de
``AgentSpec`` (apenas especificação). Esta factory traduz cada
``AgentSpec.role`` em uma classe de especialista BR concreta.

Heurísticas de mapeamento role -> especialista são tolerantes a
sinônimos em pt-BR (atendente / atendimento, vendas / comercial,
agendamento / recepção etc.).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

from .prompts import PROMPTS_BY_ROLE

logger = logging.getLogger(__name__)

# Sinônimos pt-BR -> role canônico. Ordem importa em casos ambíguos
# (ex. 'recepcao' antes de 'agendamento' por causa de clínica).
# Contexto de saúde: se qualquer um aparecer, recepcionista_saude
# tem prioridade sobre agendamento/atendente para evitar misturar
# secretaria clínica com agendamento genérico.
# Nota: 'consulta' SOZINHO é ambíguo (consultoria) — fica de fora.
_HEALTH_CONTEXT_KEYWORDS = (
    "clinica",
    "consultorio",
    "medico",
    "medica",
    "dentista",
    "odonto",
    "saude",
    "paciente",
)

_ROLE_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "recepcionista_saude",
        [
            "recepcionista de saude",
            "recepcionista saude",
            "recepcao clinica",
            "recepcao medica",
            "secretaria clinica",
            "secretaria medica",
            "agenda medica",
            "recepcao da clinica",
            "recepcao do consultorio",
        ],
    ),
    (
        "agendamento",
        [
            "agendamento",
            "agenda",
            "marcacao",
            "recepcao",
            "secretaria",
        ],
    ),
    (
        "atendente",
        [
            "atendente",
            "atendimento",
            "sac",
            "primeiro contato",
            "whatsapp",
            "chatbot",
        ],
    ),
    (
        "vendas",
        [
            "vendas",
            "vendedor",
            "comercial",
            "pre venda",
            "qualificacao",
            "lead",
            "carrinho",
        ],
    ),
    (
        "suporte",
        [
            "suporte",
            "pos venda",
            "rastreio",
            "troca",
            "devolucao",
            "ouvidoria",
        ],
    ),
    (
        "marketing",
        [
            "marketing",
            "campanha",
            "social media",
            "midia",
            "engajamento",
            "fidelizacao",
        ],
    ),
    (
        "catalogo",
        [
            "catalogo",
            "cardapio",
            "produto",
            "estoque",
            "curadoria",
            "menu",
        ],
    ),
    (
        "financeiro",
        [
            "financeiro",
            "cobranca",
            "pix",
            "pagamento",
            "boleto",
            "conciliacao",
        ],
    ),
]


def _normalize(text: str) -> str:
    """Lowercase + remove acentos rudimentarmente para casamento."""
    if not text:
        return ""
    mapping = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
    )
    cleaned = text.translate(mapping).lower()
    return re.sub(r"[^a-z0-9 ]+", " ", cleaned).strip()


def resolve_role(spec_role: str, spec_name: str = "") -> Optional[str]:
    """Resolve um ``AgentSpec.role`` (livre) para um role canônico BR.

    Args:
        spec_role: Papel descrito pelo discovery (texto livre pt-BR).
        spec_name: Nome do agente proposto (texto livre, fallback).

    Returns:
        Um dos roles em ``PROMPTS_BY_ROLE`` (sem ``"orchestrator"``)
        ou ``None`` quando nada casa.
    """
    haystacks = [_normalize(spec_role), _normalize(spec_name)]
    health_ctx = any(
        kw in h for kw in _HEALTH_CONTEXT_KEYWORDS for h in haystacks
    )
    for canonical, keywords in _ROLE_KEYWORDS:
        for kw in keywords:
            for h in haystacks:
                if kw in h:
                    # Em contexto de saúde, 'agendamento'/'atendente'/
                    # 'recepcao' devem ser elevados para recepcionista_saude.
                    if health_ctx and canonical in (
                        "agendamento",
                        "atendente",
                    ):
                        return "recepcionista_saude"
                    return canonical
    # Sem casamento direto, mas contexto é claramente saúde
    if health_ctx:
        return "recepcionista_saude"
    return None


# --- Factory ------------------------------------------------------------


SpecialistFactory = Callable[..., object]
"""Assinatura: ``(name=..., extra_tools=...) -> ReActAgent``."""


def _make_factory(role: str) -> SpecialistFactory:
    def _build(
        name: Optional[str] = None,
        extra_tools: Optional[Iterable[Callable]] = None,
        max_iters: int = 8,
    ):
        # Import local para manter import do pacote leve.
        from .specialists.base import build_specialist

        return build_specialist(
            role=role,
            name=name,
            extra_tools=extra_tools,
            max_iters=max_iters,
        )

    _build.__name__ = f"build_{role}"
    _build.__doc__ = (
        f"Constrói um especialista BR do papel {role!r} "
        "(wrapper sobre build_specialist)."
    )
    return _build


SPECIALIST_REGISTRY: dict[str, SpecialistFactory] = {
    role: _make_factory(role)
    for role in PROMPTS_BY_ROLE
    if role != "orchestrator"
}


@dataclass
class TeamBuildResult:
    """Resultado do ``build_team_from_blueprint``."""

    specialists: list = field(default_factory=list)
    """Lista de ``BRSpecialistAgent`` instanciados."""

    skipped: list[dict] = field(default_factory=list)
    """Specs do blueprint que não casaram com um role canônico."""

    role_map: dict[str, str] = field(default_factory=dict)
    """``spec.name`` -> role canônico resolvido."""


def build_team_from_blueprint(
    blueprint,
    instantiate: bool = True,
) -> TeamBuildResult:
    """Materializa o blueprint do discovery em sub-agentes BR.

    Args:
        blueprint: Instância de ``jotaduo.discovery.state.TeamBlueprint``
            (ou objeto com ``proposed_team: list[AgentSpec]``).
        instantiate: Se ``True``, instancia os ``ReActAgent``. Se
            ``False``, apenas resolve o mapping (útil para CLI/preview
            sem custo de modelo).

    Returns:
        ``TeamBuildResult`` com agentes, role_map e specs descartadas.
    """
    proposed = getattr(blueprint, "proposed_team", []) or []
    result = TeamBuildResult()
    for spec in proposed:
        spec_role = getattr(spec, "role", "") or ""
        spec_name = getattr(spec, "name", "") or ""
        canonical = resolve_role(spec_role, spec_name)
        if canonical is None:
            result.skipped.append(
                {"name": spec_name, "role": spec_role},
            )
            logger.warning(
                "br_team: não resolvi role para spec name=%r role=%r",
                spec_name,
                spec_role,
            )
            continue
        result.role_map[spec_name or canonical] = canonical
        if instantiate:
            factory = SPECIALIST_REGISTRY[canonical]
            result.specialists.append(
                factory(name=spec_name or f"BR_{canonical}"),
            )
    logger.info(
        "br_team: blueprint -> %d especialistas (%d descartados)",
        len(result.specialists) if instantiate else len(result.role_map),
        len(result.skipped),
    )
    return result
