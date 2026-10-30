"""Prueba el agente en la terminal, SIN WhatsApp.

Ideal para desarrollar y, sobre todo, para tus DEMOS DE VENTA: abres esto,
escribes como si fueras un paciente, y el dueño del negocio ve a su
"recepcionista" contestar en vivo. Solo necesitas ANTHROPIC_API_KEY en .env.

Uso:
    python chat_local.py                          # usa el primer tenant
    python chat_local.py clinica-dental-sonrisa   # tenant especifico
"""
import sys

from app import store
from app.agent import reply
from app.tenants import registry


def main() -> None:
    store.init_db()
    slug = sys.argv[1] if len(sys.argv) > 1 else None
    tenant = registry.by_slug(slug) if slug else (registry.all()[0] if registry.all() else None)
    if tenant is None:
        print("No hay tenants. Crea un YAML en la carpeta 'tenants/'.")
        return

    customer = "demo-terminal"
    print(f"\n=== Demo: {tenant.name} ===")
    print("(escribe 'salir' para terminar)\n")
    while True:
        try:
            text = input("Tú (cliente): ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in {"salir", "exit", "quit"}:
            break
        if not text:
            continue
        answer = reply(tenant, customer, "Cliente Demo", text)
        print(f"\n🤖 {tenant.name}: {answer}\n")


if __name__ == "__main__":
    main()
