# Communication Platform Core

Self-contained Flask module for inbound email processing, subscription authority, and dashboard analytics. Designed to layer on top of an existing Flask application without modifying existing files.

## Architecture

```
Incoming Webhook (Resend/SES/Postal)
        ↓
Webhook Gateway (blueprints/webhooks/)
        ↓
Provider Abstraction (providers/)
        ↓
Parser Service → Webhook Service
        ↓
Repository Layer (repositories/)
        ↓
Database Models (models/)
        ↓
Dashboard API (blueprints/dashboard/)
```

## OOP Principles Applied

| Principle | Implementation |
|-----------|---------------|
| **Encapsulation** | Internal state (`_spam_score`, `_verified`) protected behind methods/properties |
| **Inheritance** | `BaseModel` provides `id`, `created_at`, `updated_at` to all entities |
| **Abstraction** | `EmailProvider` hides webhook complexity; swap Resend → SES without touching business logic |
| **Polymorphism** | `provider.receive()` behaves differently for ResendProvider, SESProvider, PostalProvider |
| **Properties** | `Message.preview`, `Message.is_spam`, `Message.attachment_count` are computed values |

## Installation

1. Copy the `comm_platform/` folder into your project root.
2. In your existing `app.py`, add **one line**:

```python
from comm_platform import init_comm_platform
init_comm_platform(app)
```

3. Run migrations to create new tables:
```bash
flask db migrate -m "Add comm_platform tables"
flask db upgrade
```

## API Endpoints

### Webhooks
- `POST /webhooks/resend/inbound` — Resend inbound email
- `POST /webhooks/ses/inbound` — AWS SES inbound (stub)

### Mail
- `GET /mail/inbox?limit=50&offset=0` — List inbox
- `GET /mail/<id>` — Read full message
- `POST /mail/<id>/read` — Mark as read
- `POST /mail/<id>/archive` — Archive message
- `GET /mail/search?q=query` — Full-text search

### Subscribers
- `GET /subscribers?tag=&plan=&status=` — List/filter audience
- `POST /subscribers` — Register new subscriber
- `POST /subscribers/<email>/confirm` — Confirm subscription
- `POST /subscribers/<email>/unsubscribe` — Unsubscribe
- `PUT /subscribers/<email>/plan` — Change plan

### Dashboard
- `GET /dashboard/stats` — Aggregate metrics
- `GET /dashboard/health` — Health check

## Configuration

All configuration is via environment variables. See `.env.example` for required keys.


## Testing

Tests use an isolated in-memory SQLite database — your existing `sbeae.db` is never touched:

```bash
cd comm_platform
pytest tests/ -v
```

## Future Migration Path

When ready to extract into a standalone service:

1. Move `comm_platform/` to a new repo.
2. Replace `from utils.extensions import db` with a dedicated SQLAlchemy instance.
3. Add Docker + `docker-compose.yml`.
4. Swap SQLite → PostgreSQL/Oracle with zero model changes (repository pattern handles it).

## License

Same as parent project.
