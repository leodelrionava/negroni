"""Nucleo del agente: arma el contexto, llama a Claude y resuelve tool use.

Incluye prompt caching sobre el system prompt del tenant (se reutiliza en cada
mensaje de la misma conversacion -> baja el costo por mensaje de forma notable).
"""
from __future__ import annotations

import datetime as dt

from anthropic import Anthropic

from . import store, tools
from .config import settings
from .tenants import Tenant

_client = Anthropic(api_key=settings.anthropic_api_key)

MAX_TOOL_ITERATIONS = 5


def _system_blocks(tenant: Tenant) -> list[dict]:
    now = dt.datetime.now().strftime("%A %Y-%m-%d %H:%M")
    base = (
        f"{tenant.system_prompt}\n\n"
        f"--- Reglas operativas ---\n"
        f"- Responde SIEMPRE en el idioma del cliente; por defecto {tenant.language}.\n"
        f"- Sé breve y natural, como un mensaje de WhatsApp. Nada de respuestas largas.\n"
        f"- Nunca inventes precios, horarios o disponibilidad que no te hayan dado.\n"
        f"- Si no sabes algo, ofrece tomar los datos y que el equipo confirme.\n"
        f"- Negocio: {tenant.name}."
    )
    # cache_control marca el prefijo cacheable (system prompt estable del tenant).
    # La hora va en un bloque aparte, despues del corte: si quedara dentro del
    # prefijo, cambiaria cada minuto y el cache nunca se reutilizaria.
    return [
        {"type": "text", "text": base, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": f"Hoy es {now} (zona {tenant.timezone})."},
    ]


def reply(tenant: Tenant, customer: str, customer_name: str, user_text: str) -> str:
    """Procesa un mensaje del cliente y devuelve la respuesta del agente."""
    store.save_message(tenant.slug, customer, "user", [{"type": "text", "text": user_text}])

    messages = store.recent_history(tenant.slug, customer, settings.history_turns)
    tool_schemas = tools.schemas_for(tenant)

    final_text = ""
    for _ in range(MAX_TOOL_ITERATIONS):
        resp = _client.messages.create(
            model=settings.agent_model,
            max_tokens=1024,
            system=_system_blocks(tenant),
            tools=tool_schemas,
            messages=messages,
        )

        assistant_content = [block.model_dump() for block in resp.content]
        messages.append({"role": "assistant", "content": assistant_content})
        store.save_message(tenant.slug, customer, "assistant", assistant_content)

        text_parts = [b.text for b in resp.content if b.type == "text"]
        if text_parts:
            final_text = "\n".join(text_parts).strip()

        if resp.stop_reason != "tool_use":
            break

        # Ejecuta cada herramienta solicitada y devuelve los resultados.
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                result = tools.execute(tenant, customer, customer_name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        tool_msg = {"role": "user", "content": tool_results}
        messages.append(tool_msg)
        store.save_message(tenant.slug, customer, "user", tool_results)

    return final_text or "Disculpa, ¿me lo puedes repetir? 🙏"
