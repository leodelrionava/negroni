# Negroni — Multi-tenant AI receptionist for WhatsApp

An AI agent that answers a business's WhatsApp 24/7: it handles questions, books
appointments, captures leads and hands off to a human when needed. A single deployment
serves **many businesses (tenants)**; each one is a YAML file, not code.

**Stack:** Python · FastAPI · Claude API (tool use + prompt caching) · WhatsApp Cloud API · SQLite

> Status: working prototype, not in production. The included tenant
> (`clinica-dental-sonrisa.yaml`) is fictitious.

## Design decisions

- **A tenant is data, not code.** Incoming webhooks are routed by `phone_number_id` to a
  tenant defined in `tenants/*.yaml` (persona, business facts, prices, handoff contact).
  Onboarding a new business means adding a file — if a business name ever has to be
  written inside `app/`, that is a bug.
- **Idempotent webhook handling.** WhatsApp retries deliveries. A reprocessed message must
  never book the same appointment twice or duplicate a lead; message IDs are deduplicated
  in `store.py`.
- **Grounded answers only.** The agent is instructed to use only the facts in the tenant
  file and never invent prices, hours or availability; when unsure it collects the
  customer's details for staff to confirm.
- **Escalate rather than guess.** Upset customers, complex medical questions or explicit
  requests for a person trigger `handoff_to_human`.
- **Bounded tool loop.** The agent resolves tool calls in a loop capped at 5 iterations.
- **Storage behind one module.** All persistence goes through `store.py`, so SQLite can be
  swapped for Postgres without touching the rest of the code.

## Agent tools

| Tool | Purpose |
|---|---|
| `book_appointment` | Records name, service and preferred time once all three are known |
| `capture_lead` | Saves interest that did not turn into a booking |
| `handoff_to_human` | Escalates the conversation to the business's contact |

## Structure

```
app/
  config.py     Settings from environment (.env)
  tenants.py    Tenant loading and routing by phone_number_id
  store.py      SQLite: conversation history, appointments, leads, idempotency
  whatsapp.py   WhatsApp Cloud API client and webhook parsing
  tools.py      Agent tools (book, capture lead, hand off)
  agent.py      Claude core: context, tool-use loop, prompt caching
  main.py       FastAPI webhook (GET verifies, POST receives)
tenants/
  clinica-dental-sonrisa.yaml   Example tenant (fictitious)
chat_local.py   Talk to the agent in the terminal — no WhatsApp needed
```

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env   # set ANTHROPIC_API_KEY; that is enough for the terminal demo

python chat_local.py                          # try the agent without WhatsApp
uvicorn app.main:app --reload --port 8000     # run the webhook server
```

`chat_local.py` exercises the full agent — tools included — without spending WhatsApp
messages or depending on a public webhook. A full conversation there is the evidence the
agent behaves; the server starting up is not.

## Connecting WhatsApp Cloud API

1. Create a **Business** app at [developers.facebook.com](https://developers.facebook.com)
   and add the **WhatsApp** product.
2. Put the number's `phone_number_id` in the tenant YAML and the access token in `.env`.
3. Expose port 8000 (e.g. `ngrok http 8000`) or deploy to a server.
4. Configure the webhook in Meta: callback `https://YOUR_DOMAIN/webhook`, verify token =
   `WHATSAPP_VERIFY_TOKEN`, subscribe to the `messages` field.

## Roadmap

- [ ] Live availability via Google Calendar
- [ ] Voice notes (transcription) and images
- [ ] Self-service web panel for tenants
- [ ] Weekly email report per business (conversations, bookings, leads)
- [ ] Automatic appointment reminders
