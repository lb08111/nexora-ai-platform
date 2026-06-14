# -*- coding: utf-8 -*-
"""Focus NFe provider implementation for Jotaduo Fiscal.

Focus NFe authentication uses HTTP Basic Auth with the API token as the
username and an empty password. Homologacao is the safe default.
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx

from .base import AbstractFiscalProvider, FiscalResult, fiscal_response

logger = logging.getLogger("jotaduo").getChild(
    "plugin.jotaduo-fiscal.providers.focus_nfe",
)


class FocusNFeProvider(AbstractFiscalProvider):
    """Provider adapter for the Focus NFe REST API."""

    provider_name = "focus_nfe"
    BASE_URLS = {
        "homologacao": "https://homologacao.focusnfe.com.br",
        "producao": "https://api.focusnfe.com.br",
    }

    def __init__(
        self, *args: Any, timeout_s: float = 30.0, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.timeout_s = timeout_s
        self.base_url = self.BASE_URLS.get(
            self.ambiente,
            self.BASE_URLS["homologacao"],
        )

    async def emitir_nfe(self, payload: dict[str, Any]) -> FiscalResult:
        """Issue NF-e using POST /v2/nfe?ref={referencia}."""
        ref = payload.get("referencia") or self._make_reference("nfe")
        body = self._with_empresa(payload)
        return await self._request(
            "POST",
            "/v2/nfe",
            params={"ref": ref},
            json=body,
        )

    async def emitir_nfse(self, payload: dict[str, Any]) -> FiscalResult:
        """Issue NFS-e using POST /v2/nfse?ref={referencia}."""
        ref = payload.get("referencia") or self._make_reference("nfse")
        body = self._with_empresa(payload)
        return await self._request(
            "POST",
            "/v2/nfse",
            params={"ref": ref},
            json=body,
        )

    async def emitir_nfce(self, payload: dict[str, Any]) -> FiscalResult:
        """Issue NFC-e using POST /v2/nfce?ref={referencia}."""
        ref = payload.get("referencia") or self._make_reference("nfce")
        body = self._with_empresa(payload)
        return await self._request(
            "POST",
            "/v2/nfce",
            params={"ref": ref},
            json=body,
        )

    async def consultar_nota(self, chave_acesso: str) -> FiscalResult:
        """Query an invoice by Focus reference or access key."""
        path = f"/v2/nfe/{quote(chave_acesso, safe='')}"
        return await self._request("GET", path)

    async def cancelar_nota(
        self,
        chave_acesso: str,
        justificativa: str,
    ) -> FiscalResult:
        """Cancel an NF-e by Focus reference/access key."""
        path = f"/v2/nfe/{quote(chave_acesso, safe='')}"
        return await self._request(
            "DELETE",
            path,
            params={"justificativa": justificativa},
        )

    async def carta_correcao(
        self,
        chave_acesso: str,
        correcao: str,
    ) -> FiscalResult:
        """Issue a Carta de Correcao Eletronica for NF-e."""
        path = f"/v2/nfe/{quote(chave_acesso, safe='')}/carta_correcao"
        return await self._request("POST", path, json={"correcao": correcao})

    async def inutilizar_numeracao(
        self,
        serie: int,
        numero_inicial: int,
        numero_final: int,
        justificativa: str,
    ) -> FiscalResult:
        """Void an unused NF-e number range."""
        payload = {
            "serie": serie,
            "numero_inicial": numero_inicial,
            "numero_final": numero_final,
            "justificativa": justificativa,
            "cnpj_emitente": self.empresa_cnpj,
        }
        return await self._request(
            "POST", "/v2/nfe/inutilizacao", json=payload
        )

    async def baixar_xml_danfe(
        self,
        chave_acesso: str,
        formato: str = "pdf",
    ) -> FiscalResult:
        """Download XML or DANFE/PDF from Focus NFe."""
        safe_key = quote(chave_acesso, safe="")
        suffix = "xml" if formato == "xml" else "pdf"
        result = await self._request(
            "GET",
            f"/v2/nfe/{safe_key}.{suffix}",
            expect_binary=True,
        )
        return result

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        expect_binary: bool = False,
    ) -> FiscalResult:
        """Execute a Focus NFe HTTP call or return sandbox stub data."""
        if self.api_key == "sandbox":
            logger.info("Focus NFe sandbox stub: %s %s", method, path)
            return fiscal_response(
                ok=False,
                data={
                    "provider": self.provider_name,
                    "ambiente": self.ambiente,
                    "method": method,
                    "path": path,
                    "params": params or {},
                    "payload": json or {},
                },
                error=(
                    "Focus NFe sandbox stub: configure FISCAL_API_KEY with "
                    "a real token to perform this operation."
                ),
            )

        url = f"{self.base_url}{path}"
        headers = {"Accept": "application/json"}
        try:
            async with httpx.AsyncClient(
                auth=(self.api_key, ""),
                timeout=self.timeout_s,
            ) as client:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            logger.warning(
                "Focus NFe HTTP error on %s %s: %s", method, path, exc
            )
            return fiscal_response(False, None, f"Focus NFe HTTP error: {exc}")

        data: Any
        if expect_binary and response.is_success:
            data = {
                "content_type": response.headers.get("content-type"),
                "content_base64": base64.b64encode(response.content).decode(
                    "ascii"
                ),
            }
        else:
            data = self._decode_response(response)

        if response.is_success:
            return fiscal_response(True, data, None)
        return fiscal_response(
            False,
            data,
            {
                "status_code": response.status_code,
                "message": "Focus NFe returned an error response.",
            },
        )

    def _with_empresa(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = dict(payload)
        body.setdefault("cnpj_emitente", self.empresa_cnpj)
        if self.empresa_ie:
            body.setdefault("inscricao_estadual_emitente", self.empresa_ie)
        body.setdefault("regime_tributario", self.regime_tributario)
        return body

    @staticmethod
    def _decode_response(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text

    @staticmethod
    def _make_reference(prefix: str) -> str:
        return f"jotaduo-{prefix}-{int(time.time() * 1000)}"
