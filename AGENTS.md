# Negroni

Recepcionista de IA por WhatsApp, multi-tenant. Un solo despliegue atiende a muchos clientes; cada uno se configura con un YAML en `tenants/`. Python, FastAPI, Claude API y WhatsApp Cloud API.

> La descripción completa, la estructura y el despliegue están en [`README.md`](README.md). **Empieza ahí.**

## Comandos

```powershell
python -m venv .venv; .\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload      # servidor
python chat_local.py               # probar el agente sin WhatsApp
```

`chat_local.py` es la vía para iterar sobre el comportamiento del agente **sin gastar mensajes de WhatsApp ni depender del webhook**. Usarlo antes de probar contra el canal real.

## Un cliente es un archivo, no código

El ruteo va por `phone_number_id`, y cada cliente vive como un YAML en `tenants/`. **Dar de alta un cliente no debería requerir tocar código.** Si algo obliga a escribir el nombre de un negocio dentro de `app/`, es señal de que falta moverlo al YAML.

## Estructura

```
app/config.py     configuracion desde .env
app/tenants.py    carga y ruteo de clientes por phone_number_id
app/store.py      sqlite: historial, citas, leads, idempotencia
app/whatsapp.py   cliente de WhatsApp Cloud API y parseo de webhooks
app/tools.py      herramientas del agente: agendar, capturar lead, escalar
tenants/          un YAML por cliente
chat_local.py     consola para probar el agente sin WhatsApp
```

## Restricciones

- **`.env` tiene las llaves de Claude y de WhatsApp Cloud API.** No escribir ahí desde un agente; si falta una variable, documentarla y pedirla.
- **La idempotencia importa:** WhatsApp reintenta los webhooks. Un mensaje reprocesado no debe agendar dos veces la misma cita ni duplicar un prospecto. Está resuelto en `store.py`; cualquier camino nuevo tiene que respetarlo.
- Un agente que agenda citas toca la agenda de un negocio real. Ante duda, escalar a humano antes que inventar.

## Reportar

La evidencia es una conversación completa en `chat_local.py`, o el mensaje real recibido en WhatsApp. Que el servidor levante no prueba que el agente se comporte.
