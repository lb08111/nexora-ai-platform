# -*- coding: utf-8 -*-
"""Costura ao vivo: dirige o discovery agent real um turno por vez.

``LiveDiscoverySession`` implementa a Protocol ``DiscoverySession`` de
``discovery/session.py`` (``async next_turn(user_message) -> TurnResult``),
mantendo a ``InterviewSession`` / ``DiscoveryState`` / ``Agent`` vivos entre
chamadas (o router guarda uma instância por ``session_id``).

- ``next_turn(None)`` -> roda o primeiro passo (sem resposta do usuário) e
  devolve a 1ª pergunta + snapshot do estado (``done=False``).
- ``next_turn(texto)`` -> injeta a resposta, o agente roda ``reflect`` +
  próxima pergunta; devolve pergunta + estado.
- Quando o critério de parada dispara (o agente chamou ``emit_blueprint`` ou
  ``state.ready_to_emit()``), devolve ``TurnResult`` com o ``blueprint`` (dict
  do ``TeamBlueprint``) e ``done=True``, ``question=None``.

``make_live_session_factory`` devolve uma fábrica
``() -> LiveDiscoverySession`` para
``app/routers/discovery_stream.set_session_factory``. O wiring fica atrás
da env ``QWENPAW_DISCOVERY_LIVE`` para que a ``ScriptedDiscoverySession`` siga
como default seguro (ela continua existindo p/ testes/offline).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from agentscope.message import Msg

from . import runner as runner_mod
from .session import TurnResult
from .state import DiscoveryState, OpenArea, TeamBlueprint, Turn
from .tools import InterviewSession

_OPENING = (
    "Inicie a entrevista: cumprimente brevemente o empresário e faça a "
    "primeira pergunta para entender o que a empresa faz."
)


def _seed_area() -> OpenArea:
    return OpenArea(
        id="segmento",
        topic="qual o segmento/negócio da empresa",
        confidence=0.0,
        priority=5,
    )


class LiveDiscoverySession:
    """Sessão de discovery dirigida pelo agente real, um turno por vez."""

    def __init__(
        self,
        session_id: str | None = None,
        out_dir: Path | str | None = None,
    ) -> None:
        self.session_id = session_id or uuid4().hex[:8]
        if out_dir is None:
            out_dir = Path(tempfile.gettempdir()) / (
                f"qwenpaw-discovery-{self.session_id}"
            )
        self._state = DiscoveryState(session_id=self.session_id)
        self._state.open_areas.append(_seed_area())
        self._session = InterviewSession(self._state, out_dir=Path(out_dir))
        # Construído via o módulo runner p/ herdar o monkeypatch nos testes.
        self._agent = runner_mod.build_discovery_agent(self._session)

    async def next_turn(self, user_message: str | None) -> TurnResult:
        """Avança a entrevista em um turno (None abre a entrevista)."""
        prompt = _OPENING if user_message is None else user_message
        # Paridade com o runner: registra a resposta do empresário no
        # transcript do estado (None abre a entrevista, nada a registrar).
        if user_message is not None:
            self._state.transcript.append(
                Turn(role="user", text=user_message),
            )
        reply = await self._agent.reply(
            Msg(role="user", name="user", content=prompt),
        )

        if self._is_done():
            return TurnResult(
                state=self._snapshot(),
                question=None,
                blueprint=self._blueprint_dict(),
                done=True,
            )

        question = reply.get_text_content() or ""
        if question:
            self._state.transcript.append(
                Turn(role="assistant", text=question),
            )
        return TurnResult(
            state=self._snapshot(),
            question=question,
            blueprint=None,
            done=False,
        )

    # --- helpers ---------------------------------------------------------

    def _is_done(self) -> bool:
        # O agente gravar o blueprint é o sinal de parada canônico.
        if self._session.emitted:
            return True
        # Fallback ``ready_to_emit``: encerra quando o perfil mínimo (segmento)
        # está preenchido E toda área prioritária (priority>=3) foi satisfeita
        # — seja por confiança alta, seja por ter sido fechada via
        # ``close_area_ids``. NÃO exigimos que ainda haja área crítica
        # *aberta*:
        # como fechar áreas as remove de ``open_areas``, esse antigo
        # guard ``critical_exists`` travava o fim assim que o agente concluía
        # todas as ramificações. O perfil mínimo já basta para evitar um
        # blueprint degenerado (a área-semente ``segmento`` começa com
        # confiança 0, então ``ready_to_emit`` segura o fim prematuro no
        # primeiro turno).
        has_profile = bool(self._state.company.segment)
        return has_profile and self._state.ready_to_emit()

    def _snapshot(self) -> dict[str, Any]:
        return self._state.model_dump(mode="json")

    def _blueprint_dict(self) -> dict[str, Any]:
        """Dict do ``TeamBlueprint`` (contrato lido por a2ui/builder.py).

        Quando o agente já gravou ``blueprint.json`` (``emit_blueprint``),
        reusa esse arquivo validado; senão, deriva um blueprint mínimo do
        estado corrente.
        """
        bp_path = self._session.out_dir / "blueprint.json"
        if self._session.emitted and bp_path.exists():
            raw = json.loads(bp_path.read_text(encoding="utf-8"))
            return TeamBlueprint.model_validate(raw).model_dump(mode="json")
        return self._derive_blueprint_from_state().model_dump(mode="json")

    def _derive_blueprint_from_state(self) -> TeamBlueprint:
        """Blueprint mínimo a partir do estado (fallback ``ready_to_emit``)."""
        return TeamBlueprint(
            company_profile=self._state.company,
            detected_integrations=list(self._state.integrations),
            open_questions=[a.topic for a in self._state.open_areas],
        )


def make_live_session_factory() -> Callable[[], LiveDiscoverySession]:
    """Factory usada pelo router para criar sessões ao vivo sob demanda."""
    return LiveDiscoverySession
