# SBEAE — Session-Bound Event Authorization Engine

Flask-based identity + session + event authority for your Django CRM.

## Two-sentence summary
Django handles your product. Flask owns identity, sessions, risk scoring,
event validation, and subscription enforcement. Django only ever sees
`{"status": "allow|deny|throttle", "session_id": "...", "reason": "..."}`.

---

## Install & run (Termux-friendly — 2 dependencies)

```bash
pip install flask requests
python app.py          # listens on 127.0.0.1:5050
```

---

## Architecture layers

```
┌─────────────────────────────────────────────────────┐
│  Layer 4 — Event Layer                              │
│  Actions live INSIDE a session. Never across.       │
├─────────────────────────────────────────────────────┤
│  Layer 3 — Session Layer  ← HARD BOUNDARY           │
│  session_id is the truth anchor.                    │
├─────────────────────────────────────────────────────┤
│  Layer 2 — Device Layer                             │
│  fingerprint_hash is a SOFT SIGNAL, not a join key. │
├─────────────────────────────────────────────────────┤
│  Layer 1 — Identity Layer                           │
│  user_id                                            │
└─────────────────────────────────────────────────────┘
```

---

## Key design decisions

### Session as hard boundary (fixes event collision)
`SessionGuard.validate()` rejects any event whose `session_id` does not
match the claimed `user_id`. Cross-session identity merging is
**structurally impossible** — there is no merge path in the code.

### Fingerprint as soft signal only
`device_fingerprint` on a session is stored for risk scoring only.
It is never used as a join key or identity source.

### Polymorphic events
`BaseEvent.process()` is the only interface Django's client ever calls.
`LoginEvent`, `ActionEvent`, `BillingEvent`, `AbuseEvent` each own their
own behaviour.

### Risk scoring is additive and isolated
`RiskEngine` is a pure scoring function (no I/O).
`RiskService` owns persistence. They are separate on purpose.

---

## API surface (all POST, JSON body)

| Endpoint | Auth | Description |
|---|---|---|
| `POST /auth/register` | service secret | Create user |
| `POST /auth/login` | service secret | Authenticate + create session |
| `POST /auth/logout` | service secret | Revoke session |
| `POST /session/validate` | service secret | Check session validity |
| `POST /session/revoke` | service secret | Revoke one session |
| `POST /session/revoke-all` | service secret | Revoke all user sessions |
| `POST /session/list` | service secret | List active sessions |
| `POST /event/process` | service secret + valid session | Process any event |
| `POST /webhook/monnify` | HMAC signature | Billing webhook |
| `GET /health` | none | Liveness check |

---

## Django integration (one file)

Copy `django_client.py` into your Django project:

```python
from flask_client import SBEAEClient
client = SBEAEClient()

# Login
result = client.login(email, password, fingerprint_hash)
session_id = result["session_id"]

# Every Django view
result = client.validate_session(session_id, request.user.id)
if result["status"] != "allow":
    return HttpResponseForbidden(result["reason"])

# Any CRM action
result = client.process_event(session_id, user_id, "action", payload)
# result = {"status": "allow|deny|throttle", "risk_score": int, ...}
```

---

## Decision output (what Django always receives)

```json
{
  "status": "allow",
  "session_id": "abc123...",
  "risk_score": 2,
  "risk_status": "ok"
}
```

---

## File structure

```
flask_auth_engine/
├── app.py                  ← entry point
├── config.py               ← all env config
├── store.py                ← in-memory repos (swap for SQLAlchemy)
├── requirements.txt        ← flask + requests only
├── django_client.py        ← drop into Django project
│
├── models/
│   └── models.py           ← User, Session, Event, Risk, Subscription, Fingerprint
│
├── services/
│   ├── auth_service.py     ← credential validation
│   └── services.py         ← Session, Fingerprint, Risk, Subscription, Event services
│
├── engine/
│   └── engine.py           ← BaseEvent hierarchy, EventRouter, SessionGuard,
│                              RiskEngine, SubscriptionGuard
│
├── controllers/
│   └── controllers.py      ← auth, event, session, webhook blueprints
│
└── middleware/
    └── middleware.py       ← service auth, session validation, rate limiting
```

---

## Swap store.py for persistence

The entire `store.py` module is the only layer that touches data.
Services import only from `store.*`. To add SQLAlchemy:

1. Replace `UserStore`, `SessionStore`, etc. with SQLAlchemy-backed classes.
2. Keep the same method signatures.
3. Nothing else changes.
