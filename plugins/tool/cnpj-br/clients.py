# -*- coding: utf-8 -*-
"""Clientes HTTP assíncronos para BrasilAPI e ReceitaWS."""

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "jotaduo-ai-platform/1.0 cnpj-br-plugin"}
_CACHE: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}


class _BaseHttpClient:
    """HTTP client with timeout, user-agent and lightweight TTL cache."""

    BASE = ""
    FONTE = ""

    def __init__(self, timeout: float = 15.0, cache_ttl_seconds: int = 3600):
        self.timeout = float(timeout)
        self.cache_ttl_seconds = int(cache_ttl_seconds)

    def _cache_get(
        self,
        endpoint: str,
        identifier: str,
    ) -> dict[str, Any] | None:
        if self.cache_ttl_seconds <= 0:
            return None
        key = (endpoint, identifier)
        cached = _CACHE.get(key)
        if not cached:
            return None
        timestamp, payload = cached
        if time.time() - timestamp > self.cache_ttl_seconds:
            _CACHE.pop(key, None)
            return None
        return dict(payload)

    def _cache_set(
        self,
        endpoint: str,
        identifier: str,
        payload: dict[str, Any],
    ) -> None:
        if self.cache_ttl_seconds > 0:
            _CACHE[(endpoint, identifier)] = (time.time(), dict(payload))

    async def _get(self, endpoint: str, identifier: str) -> dict[str, Any]:
        cached = self._cache_get(endpoint, identifier)
        if cached is not None:
            return cached

        url = f"{self.BASE}{endpoint.format(identifier=identifier)}"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=_HEADERS,
            ) as client:
                response = await client.get(url)
        except httpx.TimeoutException:
            logger.warning("Timeout calling %s", url)
            return {
                "ok": False,
                "error": "Tempo esgotado ao consultar a fonte pública.",
                "status_code": None,
                "fonte": self.FONTE,
            }
        except httpx.HTTPError as exc:
            logger.warning("HTTP error calling %s: %s", url, exc)
            return {
                "ok": False,
                "error": "Falha de comunicação com a fonte pública.",
                "status_code": None,
                "fonte": self.FONTE,
            }

        if response.status_code == 429:
            return {
                "ok": False,
                "error": "Limite de requisições atingido na fonte pública.",
                "status_code": 429,
                "fonte": self.FONTE,
            }

        if response.status_code >= 400:
            logger.info(
                "Provider %s returned %s for %s",
                self.FONTE,
                response.status_code,
                url,
            )
            return {
                "ok": False,
                "error": "Registro não encontrado ou indisponível na fonte pública.",
                "status_code": response.status_code,
                "fonte": self.FONTE,
            }

        try:
            payload = response.json()
        except ValueError:
            return {
                "ok": False,
                "error": "Resposta inválida recebida da fonte pública.",
                "status_code": response.status_code,
                "fonte": self.FONTE,
            }

        if isinstance(payload, dict):
            self._cache_set(endpoint, identifier, payload)
            return payload

        return {
            "ok": False,
            "error": "Resposta inesperada recebida da fonte pública.",
            "status_code": response.status_code,
            "fonte": self.FONTE,
        }


class BrasilApiClient(_BaseHttpClient):
    """Cliente da BrasilAPI, fonte pública gratuita sem chave."""

    BASE = "https://brasilapi.com.br/api"
    FONTE = "brasilapi"

    async def cnpj(self, cnpj_limpo: str) -> dict[str, Any]:
        return await self._get("/cnpj/v1/{identifier}", cnpj_limpo)

    async def cep(self, cep_limpo: str) -> dict[str, Any]:
        return await self._get("/cep/v2/{identifier}", cep_limpo)


class ReceitaWsClient(_BaseHttpClient):
    """Cliente ReceitaWS usado como fallback para consultas CNPJ."""

    BASE = "https://www.receitaws.com.br/v1"
    FONTE = "receitaws"

    async def cnpj(self, cnpj_limpo: str) -> dict[str, Any]:
        return await self._get("/cnpj/{identifier}", cnpj_limpo)
