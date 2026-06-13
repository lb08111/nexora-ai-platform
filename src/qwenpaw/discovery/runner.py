# -*- coding: utf-8 -*-
"""Loop de terminal do discovery agent + persistência da sessão.

``run_discovery_session`` conduz a entrevista no terminal (uma pergunta por
vez), persiste o ``DiscoveryState`` em ``discovery_state.json`` a cada turno e
termina quando o agente chama ``emit_blueprint`` (gravando ``blueprint.json`` e
``blueprint.md``). ``run_discovery_cli`` é o wrapper fino usado pela CLI.

``_read_user_input`` e ``build_discovery_agent`` ficam no nível do módulo de
propósito: os testes os substituem via ``monkeypatch`` para rodar a entrevista
ponta a ponta sem LLM real nem terminal.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agentscope.message import Msg

from .agent import build_discovery_agent
from .state import DiscoveryState, OpenArea, Turn
from .tools import InterviewSession

_GREETING = (
    "Olá! Vou te ajudar a montar um time de agentes para a sua empresa. "
    "Me conta: o que a sua empresa faz?"
)
_EXIT_WORDS = ("/fim", "/sair", "exit", "quit")
_CLOSE_REQUEST = (
    "Pode encerrar a entrevista e gerar o blueprint com o que já temos, "
    "listando o que ficou em aberto."
)


def _seed_area() -> OpenArea:
    """Área-semente que dá o primeiro foco da entrevista (o segmento)."""
    return OpenArea(
        id="segmento",
        topic="qual o segmento/negócio da empresa",
        confidence=0.0,
        priority=5,
    )


def _read_user_input(prompt: str) -> str:  # isolado p/ teste (monkeypatch)
    return input(prompt)


def _persist(state: DiscoveryState, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "discovery_state.json").write_text(
        state.model_dump_json(indent=2),
        encoding="utf-8",
    )


async def run_discovery_session(
    session_id: str,
    out_dir: Path,
) -> InterviewSession:
    """Conduz a entrevista no terminal e devolve a sessão (estado + flags)."""
    out_dir = Path(out_dir)
    state = DiscoveryState(session_id=session_id)
    state.open_areas.append(_seed_area())
    session = InterviewSession(state, out_dir=out_dir)
    agent = build_discovery_agent(session)

    print(_GREETING)
    _persist(state, out_dir)

    while not session.emitted:
        user_text = _read_user_input("\nVocê: ").strip()
        if user_text.lower() in _EXIT_WORDS:
            # Pede ao agente que feche com o que já sabe.
            state.transcript.append(Turn(role="user", text="/fim"))
            reply = await agent.reply(
                Msg(role="user", name="user", content=_CLOSE_REQUEST),
            )
            _persist(state, out_dir)
            print(f"\nConsultor: {reply.get_text_content()}")
            break

        state.transcript.append(Turn(role="user", text=user_text))
        reply = await agent.reply(Msg(role="user", name="user", content=user_text))
        _persist(state, out_dir)
        print(f"\nConsultor: {reply.get_text_content()}")

    if not session.emitted:
        print(
            "\n(Entrevista encerrada sem blueprint — "
            "estado salvo para retomar.)",
        )
    return session


async def run_discovery_cli(
    workspace_dir: Path | str | None = None,
) -> InterviewSession:
    """Wrapper fino: gera um ``session_id`` e roda a entrevista no terminal.

    O blueprint vai para ``<workspace_dir>/discovery/<session_id>``
    (ou ``./discovery/<session_id>`` quando ``workspace_dir`` é None).
    """
    session_id = uuid4().hex[:8]
    base = Path(workspace_dir) if workspace_dir else Path(".")
    out_dir = base / "discovery" / session_id
    return await run_discovery_session(
        session_id=session_id,
        out_dir=out_dir,
    )
