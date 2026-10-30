"""Cliente minimo de WhatsApp Cloud API (envio de mensajes + parseo de webhooks)."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from .config import settings


@dataclass
class InboundMessage:
    phone_number_id: str   # numero del negocio que recibe (clave de ruteo del tenant)
    from_wa_id: str        # numero del cliente que escribe
    name: str              # nombre de perfil del cliente (si lo comparte)
    text: str              # texto del mensaje
    wamid: str             # id unico del mensaje (para idempotencia)


def _graph_url(phone_number_id: str) -> str:
    return f"https://graph.facebook.com/{settings.graph_api_version}/{phone_number_id}/messages"


async def send_text(phone_number_id: str, token: str, to: str, body: str) -> None:
    """Envia un mensaje de texto al cliente."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body[:4096]},
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(_graph_url(phone_number_id), json=payload, headers=headers)
        resp.raise_for_status()


async def mark_read(phone_number_id: str, token: str, wamid: str) -> None:
    """Marca el mensaje como leido (los dos palomeos azules)."""
    payload = {"messaging_product": "whatsapp", "status": "read", "message_id": wamid}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(_graph_url(phone_number_id), json=payload, headers=headers)
    except httpx.HTTPError:
        pass  # no es critico


def parse_webhook(data: dict) -> list[InboundMessage]:
    """Extrae los mensajes de texto entrantes de un payload del webhook."""
    out: list[InboundMessage] = []
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            phone_number_id = str(metadata.get("phone_number_id", ""))
            contacts = {c["wa_id"]: c.get("profile", {}).get("name", "")
                        for c in value.get("contacts", [])}
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    # MVP: solo texto. Audio/imagen se agregan despues.
                    continue
                wa_id = msg.get("from", "")
                out.append(InboundMessage(
                    phone_number_id=phone_number_id,
                    from_wa_id=wa_id,
                    name=contacts.get(wa_id, ""),
                    text=msg.get("text", {}).get("body", ""),
                    wamid=msg.get("id", ""),
                ))
    return out
