"""Herramientas (tool use) que el agente puede ejecutar.

En el MVP las citas/leads se guardan en sqlite. La integracion real con Google
Calendar es un add-on de venta (sube el ticket): se cambia solo el cuerpo de
`book_appointment` sin tocar el agente.
"""
from __future__ import annotations

from . import store
from .tenants import Tenant

# Esquemas que se le exponen a Claude. Se filtran por tenant (ej. si no tiene
# agenda habilitada, no se le ofrece book_appointment).
TOOL_SCHEMAS = [
    {
        "name": "book_appointment",
        "description": (
            "Agenda una cita para el cliente. Usalo SOLO cuando ya tengas: nombre, "
            "servicio deseado y fecha/hora concreta confirmada por el cliente."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nombre del cliente"},
                "service": {"type": "string", "description": "Servicio o motivo de la cita"},
                "start_iso": {"type": "string", "description": "Fecha y hora en ISO 8601, ej. 2026-06-10T16:30:00"},
                "notes": {"type": "string", "description": "Notas adicionales (opcional)"},
            },
            "required": ["name", "service", "start_iso"],
        },
    },
    {
        "name": "capture_lead",
        "description": (
            "Guarda los datos de un prospecto interesado cuando NO se agenda cita "
            "todavia pero quieres registrar el interes para seguimiento humano."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "intent": {"type": "string", "description": "Que quiere el cliente"},
                "detail": {"type": "string", "description": "Contexto util para dar seguimiento"},
            },
            "required": ["intent"],
        },
    },
    {
        "name": "handoff_to_human",
        "description": (
            "Escala con una persona real cuando el cliente lo pide explicitamente, "
            "esta molesto, o la consulta excede lo que puedes resolver."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Por que se escala"},
            },
            "required": ["reason"],
        },
    },
]


def schemas_for(tenant: Tenant) -> list[dict]:
    tools = list(TOOL_SCHEMAS)
    if not tenant.booking_enabled:
        tools = [t for t in tools if t["name"] != "book_appointment"]
    return tools


def execute(tenant: Tenant, customer: str, name: str, args: dict) -> str:
    """Ejecuta la herramienta y devuelve un texto-resultado para el modelo."""
    if name == "book_appointment":
        appt_id = store.save_appointment(
            tenant.slug, customer,
            args.get("name", ""), args.get("service", ""),
            args.get("start_iso", ""), args.get("notes", ""),
        )
        return (f"OK. Cita #{appt_id} registrada para {args.get('name')} "
                f"el {args.get('start_iso')} ({args.get('service')}). "
                f"Confirma al cliente de forma calida.")

    if name == "capture_lead":
        lead_id = store.save_lead(
            tenant.slug, customer,
            args.get("name", ""), args.get("intent", ""), args.get("detail", ""),
        )
        return f"OK. Prospecto #{lead_id} guardado para seguimiento."

    if name == "handoff_to_human":
        contacto = tenant.handoff_number or "el equipo"
        return (f"OK. Se notificara a {contacto}. Dile al cliente que en breve "
                f"una persona del equipo lo atendera por este mismo chat.")

    return f"Herramienta desconocida: {name}"
