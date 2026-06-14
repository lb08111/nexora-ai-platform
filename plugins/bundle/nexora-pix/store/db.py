# -*- coding: utf-8 -*-
"""SQLite helper for Pix idempotency and reconciliation."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from ..constants import PIX_DB_PATH

logger = logging.getLogger("qwenpaw").getChild("plugin.nexora-pix.store.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cobrancas (
  txid TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  valor TEXT NOT NULL,
  devedor TEXT,
  status TEXT NOT NULL,
  br_code TEXT,
  e2eid TEXT,
  criada_em TEXT NOT NULL,
  pago_em TEXT,
  raw_response TEXT
);
CREATE INDEX IF NOT EXISTS idx_cob_status ON cobrancas(status);
CREATE INDEX IF NOT EXISTS idx_cob_e2eid ON cobrancas(e2eid);
"""


def _connect() -> sqlite3.Connection:
    Path(PIX_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(PIX_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    raw = data.get("raw_response")
    if raw:
        try:
            data["raw_response"] = json.loads(raw)
        except json.JSONDecodeError:
            pass
    return data


async def init_db() -> None:
    """Create the Pix SQLite schema if needed."""

    def _init() -> None:
        with _connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    await asyncio.to_thread(_init)
    logger.debug("Pix store initialized at %s", PIX_DB_PATH)


async def get_cobranca(
    txid: str,
    provider: str | None = None,
) -> dict[str, Any] | None:
    """Fetch a charge by txid and optional provider."""
    await init_db()

    def _get() -> dict[str, Any] | None:
        with _connect() as conn:
            if provider:
                row = conn.execute(
                    """
                    SELECT * FROM cobrancas
                    WHERE txid = ? AND provider = ?
                    """,
                    (txid, provider),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM cobrancas WHERE txid = ?",
                    (txid,),
                ).fetchone()
            return _row_to_dict(row)

    return await asyncio.to_thread(_get)


async def save_cobranca(
    *,
    txid: str,
    provider: str,
    valor: Decimal,
    devedor: str | None,
    status: str,
    br_code: str | None = None,
    e2eid: str | None = None,
    raw_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Insert a charge idempotently and return the stored record."""
    await init_db()
    raw = json.dumps(raw_response or {}, ensure_ascii=False)

    def _save() -> None:
        with _connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO cobrancas (
                    txid, provider, valor, devedor, status, br_code,
                    e2eid, criada_em, pago_em, raw_response
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    txid,
                    provider,
                    str(valor),
                    devedor,
                    status,
                    br_code,
                    e2eid,
                    _utc_now(),
                    None,
                    raw,
                ),
            )
            conn.commit()

    await asyncio.to_thread(_save)
    stored = await get_cobranca(txid, provider)
    if stored is None:
        raise RuntimeError(f"Failed to persist Pix charge {txid}")
    return stored


async def update_status(
    *,
    txid: str,
    provider: str,
    status: str,
    raw_response: dict[str, Any] | None = None,
    e2eid: str | None = None,
    valor: Decimal | None = None,
) -> dict[str, Any] | None:
    """Update charge status and optional payment fields."""
    await init_db()
    paid_statuses = {"RECEIVED", "CONFIRMED", "RECEBIDO", "paid", "PAID"}
    pago_em = _utc_now() if status in paid_statuses else None
    raw = json.dumps(raw_response or {}, ensure_ascii=False)

    def _update() -> None:
        with _connect() as conn:
            conn.execute(
                """
                UPDATE cobrancas
                SET status = ?,
                    e2eid = COALESCE(?, e2eid),
                    pago_em = COALESCE(?, pago_em),
                    valor = COALESCE(?, valor),
                    raw_response = CASE
                        WHEN ? != '{}' THEN ?
                        ELSE raw_response
                    END
                WHERE txid = ? AND provider = ?
                """,
                (
                    status,
                    e2eid,
                    pago_em,
                    str(valor) if valor is not None else None,
                    raw,
                    raw,
                    txid,
                    provider,
                ),
            )
            conn.commit()

    await asyncio.to_thread(_update)
    return await get_cobranca(txid, provider)


async def update_payment(
    *,
    txid: str,
    provider: str,
    valor_recebido: Decimal,
    e2eid: str,
    raw_response: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Mark a charge as paid during reconciliation."""
    await init_db()
    raw = json.dumps(raw_response or {}, ensure_ascii=False)

    def _update() -> None:
        with _connect() as conn:
            conn.execute(
                """
                UPDATE cobrancas
                SET status = 'RECEIVED',
                    valor = ?,
                    e2eid = ?,
                    pago_em = ?,
                    raw_response = CASE
                        WHEN ? != '{}' THEN ?
                        ELSE raw_response
                    END
                WHERE txid = ? AND provider = ?
                """,
                (
                    str(valor_recebido),
                    e2eid,
                    _utc_now(),
                    raw,
                    raw,
                    txid,
                    provider,
                ),
            )
            conn.commit()

    await asyncio.to_thread(_update)
    return await get_cobranca(txid, provider)


async def list_cobrancas(
    *,
    inicio_iso: str | None = None,
    fim_iso: str | None = None,
    status: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """List stored charges by creation date and optional status."""
    await init_db()

    def _list() -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if inicio_iso:
            clauses.append("criada_em >= ?")
            params.append(inicio_iso)
        if fim_iso:
            clauses.append("criada_em <= ?")
            params.append(fim_iso)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with _connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM cobrancas
                {where}
                ORDER BY criada_em DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
            return [row for row in (_row_to_dict(r) for r in rows) if row]

    return await asyncio.to_thread(_list)
