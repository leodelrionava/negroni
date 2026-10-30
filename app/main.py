"""App FastAPI: webhook de WhatsApp Cloud API (verificacion + recepcion).

Endpoints:
  GET  /webhook   -> verificacion del webhook (Meta lo llama una vez al configurar)
  POST /webhook   -> recibe mensajes entrantes
  GET  /health    -> healthcheck
  GET  /tenants   -> lista de tenants cargados (util para depurar)
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, Response

from . import agent, store, whatsapp
from .config import settings
from .tenants import registry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("negroni")

app = FastAPI(title="Negroni — Agente WhatsApp")


@app.on_event("startup")
def _startup() -> None:
    store.init_db()
    log.info("DB lista. Tenants cargados: %s", [t.slug for t in registry.all()])


@app.get("/health")
def health() -> dict:
    return {"ok": True, "tenants": len(registry.all())}


@app.get("/tenants")
def list_tenants() -> dict:
    return {
        "tenants": [
            {"slug": t.slug, "name": t.name, "phone_number_id": t.phone_number_id}
            for t in registry.all()
        ]
    }


@app.get("/webhook")
def verify(request: Request) -> Response:
    """Meta envia hub.mode/hub.verify_token/hub.challenge para validar el webhook."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        log.info("Webhook verificado por Meta.")
        return Response(content=challenge, media_type="text/plain")
    log.warning("Verificacion de webhook fallida.")
    return Response(content="forbidden", status_code=403)


@app.post("/webhook")
async def receive(request: Request) -> Response:
    """Procesa mensajes entrantes. Responde 200 rapido (Meta reintenta si no)."""
    data = await request.json()
    for msg in whatsapp.parse_webhook(data):
        if not msg.text:
            continue
        if store.already_processed(msg.wamid):
            continue

        tenant = registry.by_phone_id(msg.phone_number_id)
        if tenant is None:
            log.warning("Sin tenant para phone_number_id=%s", msg.phone_number_id)
            continue

        token = tenant.token()
        await whatsapp.mark_read(msg.phone_number_id, token, msg.wamid)

        try:
            answer = agent.reply(tenant, msg.from_wa_id, msg.name, msg.text)
        except Exception:  # nunca tiramos el webhook por un error del modelo
            log.exception("Error generando respuesta para tenant=%s", tenant.slug)
            answer = "Disculpa, tuvimos un detalle tecnico. En un momento te atiende el equipo. 🙏"

        await whatsapp.send_text(msg.phone_number_id, token, msg.from_wa_id, answer)
        log.info("[%s] %s -> %s", tenant.slug, msg.from_wa_id, answer[:80])

    return Response(content="EVENT_RECEIVED", status_code=200)
