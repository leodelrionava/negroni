"""Persistencia local en sqlite: historial de conversacion + citas + leads.

Se usa sqlite por ser cero-config y suficiente para los primeros clientes.
Cuando el volumen lo pida, se cambia a Postgres sin tocar el resto del codigo
(todo el acceso pasa por estas funciones).
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager

from .config import settings

_lock = threading.Lock()


@contextmanager
def _conn():
    con = sqlite3.connect(settings.db_path, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant    TEXT NOT NULL,
                customer  TEXT NOT NULL,
                role      TEXT NOT NULL,        -- 'user' | 'assistant'
                content   TEXT NOT NULL,        -- JSON (lista de bloques de la API)
                ts        REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_msg_convo ON messages(tenant, customer, id);

            CREATE TABLE IF NOT EXISTS appointments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant      TEXT NOT NULL,
                customer    TEXT NOT NULL,
                name        TEXT,
                service     TEXT,
                start_iso   TEXT,
                notes       TEXT,
                created_ts  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS leads (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant      TEXT NOT NULL,
                customer    TEXT NOT NULL,
                name        TEXT,
                intent      TEXT,
                detail      TEXT,
                created_ts  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS processed_messages (
                wamid TEXT PRIMARY KEY,
                ts    REAL NOT NULL
            );
            """
        )


# --- Idempotencia: WhatsApp puede reenviar el mismo webhook ---
def already_processed(wamid: str) -> bool:
    if not wamid:
        return False
    with _lock, _conn() as con:
        cur = con.execute("SELECT 1 FROM processed_messages WHERE wamid = ?", (wamid,))
        if cur.fetchone():
            return True
        con.execute(
            "INSERT INTO processed_messages(wamid, ts) VALUES (?, ?)", (wamid, time.time())
        )
        return False


# --- Historial de conversacion ---
def save_message(tenant: str, customer: str, role: str, content) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO messages(tenant, customer, role, content, ts) VALUES (?,?,?,?,?)",
            (tenant, customer, role, json.dumps(content, ensure_ascii=False), time.time()),
        )


def recent_history(tenant: str, customer: str, turns: int) -> list[dict]:
    """Devuelve los ultimos mensajes en formato de la API de Claude."""
    with _conn() as con:
        rows = con.execute(
            "SELECT role, content FROM messages WHERE tenant=? AND customer=? "
            "ORDER BY id DESC LIMIT ?",
            (tenant, customer, turns * 2),
        ).fetchall()
    rows.reverse()
    return [{"role": r["role"], "content": json.loads(r["content"])} for r in rows]


# --- Citas y leads ---
def save_appointment(tenant, customer, name, service, start_iso, notes) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO appointments(tenant, customer, name, service, start_iso, notes, created_ts) "
            "VALUES (?,?,?,?,?,?,?)",
            (tenant, customer, name, service, start_iso, notes, time.time()),
        )
        return cur.lastrowid


def save_lead(tenant, customer, name, intent, detail) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO leads(tenant, customer, name, intent, detail, created_ts) VALUES (?,?,?,?,?,?)",
            (tenant, customer, name, intent, detail, time.time()),
        )
        return cur.lastrowid
