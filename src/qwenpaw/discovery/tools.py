# -*- coding: utf-8 -*-
"""InterviewSession: estado mutável + as três tools do discovery agent.

``InterviewSession`` (não confundir com a Protocol ``DiscoverySession`` de
``discovery/session.py``) segura o ``DiscoveryState`` mutável e expõe as três
tools que o operam: ``segment_lookup``, ``reflect`` e ``emit_blueprint``. Cada
tool é ``async`` e retorna ``ToolChunk``, seguindo a convenção de
``agents/tools/get_current_time.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse, Toolkit

from .segments.taxonomy import lookup_segment
from .state import (
    OpenArea,
    ReflectUpdate,
    TeamBlueprint,
    Turn,
)
from .state import DiscoveryState  # noqa: F401  (re-export p/ tipagem)


def _ok(text: str) -> ToolResponse:
    return ToolResponse(
        content=[TextBlock(type="text", text=text)],
    )


def _blueprint_to_markdown(bp: TeamBlueprint) -> str:
    lines: list[str] = ["# Blueprint do Time de Agentes\n"]
    cp = bp.company_profile
    lines.append("## Perfil da empresa")
    lines.append(f"- Segmento: {cp.segment or '—'}")
    lines.append(f"- Porte: {cp.size or '—'}")
    lines.append(f"- Modelo de negócio: {cp.business_model or '—'}")
    if cp.pains:
        lines.append(f"- Dores: {', '.join(cp.pains)}")
    lines.append("\n## Mapa de processos")
    for p in bp.process_map:
        lines.append(f"- **{p.name}**: {p.description}")
    lines.append("\n## Integrações detectadas")
    for i in bp.detected_integrations:
        lines.append(
            f"- {i.kind} — {i.name} (dados em: {i.data_location or '—'})",
        )
    lines.append("\n## Time de agentes proposto")
    for a in bp.proposed_team:
        lines.append(f"### {a.name} — {a.role}")
        lines.append(f"- Objetivo: {a.objective}")
        if a.tasks:
            lines.append(f"- Tarefas: {', '.join(a.tasks)}")
        if a.tools_integrations:
            lines.append(f"- Integrações: {', '.join(a.tools_integrations)}")
        if a.talks_to:
            lines.append(f"- Conversa com: {', '.join(a.talks_to)}")
    lines.append("\n## Roadmap")
    for r in sorted(bp.roadmap, key=lambda x: x.order):
        lines.append(f"{r.order}. **{r.title}** — {r.rationale}")
    if bp.open_questions:
        lines.append("\n## Perguntas em aberto")
        for q in bp.open_questions:
            lines.append(f"- {q}")
    return "\n".join(lines) + "\n"


class InterviewSession:
    """Mantém o ``DiscoveryState`` e expõe as tools que o operam."""

    def __init__(self, state: DiscoveryState, out_dir: Path):
        self.state = state
        self.out_dir = Path(out_dir)
        self.emitted = False

    # --- tools -----------------------------------------------------------

    async def segment_lookup(self, description: str) -> ToolResponse:
        """Classifica o segmento da empresa pela descrição do empresário.

        Use assim que o empresário descrever o que a empresa faz. Retorna os
        'trilhos' do segmento (áreas, processos, dores e integrações típicas)
        quando a empresa cai num segmento conhecido; caso contrário sinaliza
        que você deve raciocinar livremente sobre o segmento.

        Args:
            description: O que a empresa faz, nas palavras do empresário.

        Returns:
            `ToolChunk`: trilhos do segmento, ou aviso de fallback livre.
        """
        info = lookup_segment(description)
        if info is None:
            if not any(
                a.id == "validar-segmento" for a in self.state.open_areas
            ):
                self.state.open_areas.append(
                    OpenArea(
                        id="validar-segmento",
                        topic=(
                            "validar a taxonomia deste segmento "
                            "(fora da seed)"
                        ),
                        confidence=0.1,
                        priority=4,
                    ),
                )
            return _ok(
                "Segmento não está na taxonomia curada. Raciocine de forma "
                "LIVRE sobre as áreas, processos, dores e integrações típicas "
                "deste tipo de negócio antes de continuar a entrevista.",
            )
        self.state.company.segment = info.key
        if info.cnae:
            self.state.company.cnae = info.cnae
        payload = {
            "segment_key": info.key,
            "label": info.label,
            "typical_areas": info.typical_areas,
            "typical_processes": info.typical_processes,
            "common_pains": info.common_pains,
            "common_integrations": info.common_integrations,
        }
        return _ok(
            f"Segmento identificado: {info.key} ({info.label}). Use estes "
            f"trilhos como ponto de partida e APROFUNDE com perguntas:\n"
            + json.dumps(payload, ensure_ascii=False, indent=2),
        )

    async def reflect(self, learned: str, updates_json: str) -> ToolResponse:
        """Raciocínio profundo sobre a última resposta do empresário.

        Chame ESTE tool ANTES de fazer a próxima pergunta, sempre. Atualiza o
        estado interno da entrevista: o que aprendeu, quais áreas pode fechar,
        quais novas ramificações abrir, integrações detectadas e ajustes de
        confiança. É o que torna a entrevista um raciocínio, não um formulário.

        Args:
            learned: Resumo em 1-2 frases do que ficou entendido agora.
            updates_json: JSON conforme o schema ReflectUpdate, com os campos:
                learned, close_area_ids (list[str]), new_areas (list de
                {id, topic, confidence, priority}), integrations (list de
                {kind, name, data_location, confidence}), company_updates
                (dict parcial de CompanyProfile), confidence_updates
                (dict area_id->float).

        Returns:
            `ToolChunk`: resumo do estado atualizado e a próxima área foco.
        """
        try:
            upd = ReflectUpdate.model_validate_json(updates_json)
        except Exception as exc:  # validação explícita, sem engolir
            return _ok(
                f"updates_json inválido ({exc}). Reenvie um JSON válido "
                f"conforme o schema ReflectUpdate.",
            )
        # fecha áreas
        if upd.close_area_ids:
            self.state.open_areas = [
                a
                for a in self.state.open_areas
                if a.id not in upd.close_area_ids
            ]
        # ajusta confiança
        for a in self.state.open_areas:
            if a.id in upd.confidence_updates:
                a.confidence = max(0.0, min(1.0, upd.confidence_updates[a.id]))
        # adiciona novas áreas (sem duplicar id)
        existing = {a.id for a in self.state.open_areas}
        for na in upd.new_areas:
            if na.id not in existing:
                self.state.open_areas.append(na)
                existing.add(na.id)
        # integrações (dedup por (kind,name))
        seen = {(i.kind, i.name) for i in self.state.integrations}
        for ig in upd.integrations:
            if (ig.kind, ig.name) not in seen:
                self.state.integrations.append(ig)
                seen.add((ig.kind, ig.name))
        # company
        if upd.company_updates:
            merged = self.state.company.model_dump()
            for k, v in upd.company_updates.items():
                if k in merged and v not in (None, "", []):
                    merged[k] = v
            self.state.company = type(self.state.company).model_validate(
                merged,
            )
        self.state.transcript.append(Turn(role="assistant", text=learned))

        focus = self.state.next_focus()
        focus_txt = (
            f"{focus.id} — {focus.topic}" if focus else "nenhuma (pode emitir)"
        )
        return _ok(
            f"Estado atualizado. Próxima área foco: {focus_txt}. "
            f"Pronto p/ emitir? {self.state.ready_to_emit()}",
        )

    async def emit_blueprint(self, blueprint_json: str) -> ToolResponse:
        """Valida e grava o blueprint final do time de agentes.

        Só chame quando as áreas prioritárias estiverem suficientemente
        compreendidas (ou o empresário sinalizar fim). Grava blueprint.json
        e blueprint.md no diretório da sessão.

        Args:
            blueprint_json: JSON conforme o schema TeamBlueprint.

        Returns:
            `ToolChunk`: confirmação com os caminhos, ou o erro de validação.
        """
        try:
            bp = TeamBlueprint.model_validate_json(blueprint_json)
        except Exception as exc:
            return _ok(
                f"Blueprint inválido ({exc}). Corrija o JSON conforme o "
                f"schema TeamBlueprint e chame emit_blueprint de novo.",
            )
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / "blueprint.json").write_text(
            bp.model_dump_json(indent=2),
            encoding="utf-8",
        )
        (self.out_dir / "blueprint.md").write_text(
            _blueprint_to_markdown(bp),
            encoding="utf-8",
        )
        self.emitted = True
        return _ok(
            f"Blueprint gravado em {self.out_dir / 'blueprint.json'} e "
            f"{self.out_dir / 'blueprint.md'}. Entrevista concluída.",
        )

    # --- toolkit ---------------------------------------------------------

    def build_toolkit(self) -> Toolkit:
        return Toolkit(
            tools=[
                self.segment_lookup,
                self.reflect,
                self.emit_blueprint,
            ],
        )
