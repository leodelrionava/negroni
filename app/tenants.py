"""Carga y enrutado de tenants (clientes).

Cada cliente es un archivo YAML en la carpeta TENANTS_DIR. Se enruta por el
`phone_number_id` que WhatsApp incluye en cada webhook: asi un solo deploy
atiende a todos los negocios. Esto es exactamente lo que despues se vuelve el
panel SaaS auto-servicio (Carril 2): el YAML pasa a ser un registro en BD.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

import yaml

from .config import settings


@dataclass
class Tenant:
    slug: str                      # identificador (= nombre de archivo)
    name: str                      # nombre del negocio
    phone_number_id: str           # id del numero de WhatsApp (Meta) -> clave de ruteo
    system_prompt: str             # personalidad + reglas del agente
    timezone: str = "America/Mexico_City"
    language: str = "es"
    access_token: str = ""         # token propio del cliente (opcional; si no, usa el global)
    booking_enabled: bool = True
    handoff_number: str = ""       # a quien escalar si el cliente pide humano
    metadata: dict = field(default_factory=dict)

    def token(self) -> str:
        return self.access_token or settings.whatsapp_access_token


class TenantRegistry:
    """Carga los YAML una vez y los indexa por phone_number_id."""

    def __init__(self, directory: str):
        self.directory = pathlib.Path(directory)
        self._by_phone_id: dict[str, Tenant] = {}
        self._by_slug: dict[str, Tenant] = {}
        self.reload()

    def reload(self) -> None:
        self._by_phone_id.clear()
        self._by_slug.clear()
        if not self.directory.exists():
            return
        for path in sorted(self.directory.glob("*.y*ml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            tenant = Tenant(
                slug=raw.get("slug", path.stem),
                name=raw["name"],
                phone_number_id=str(raw["phone_number_id"]),
                system_prompt=raw["system_prompt"].strip(),
                timezone=raw.get("timezone", "America/Mexico_City"),
                language=raw.get("language", "es"),
                access_token=raw.get("access_token", ""),
                booking_enabled=raw.get("booking_enabled", True),
                handoff_number=str(raw.get("handoff_number", "")),
                metadata=raw.get("metadata", {}),
            )
            self._by_phone_id[tenant.phone_number_id] = tenant
            self._by_slug[tenant.slug] = tenant

    def by_phone_id(self, phone_number_id: str) -> Tenant | None:
        return self._by_phone_id.get(str(phone_number_id))

    def by_slug(self, slug: str) -> Tenant | None:
        return self._by_slug.get(slug)

    def all(self) -> list[Tenant]:
        return list(self._by_slug.values())


registry = TenantRegistry(settings.tenants_dir)
