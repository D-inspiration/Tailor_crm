# SBEAE — Session-Bound Event Authorization Engine

Flask-based identity + session + event authority for your Django CRM.

## Quick Start

```bash
pip install -r requirements.txt
python app.py          # listens on 127.0.0.1:5050
```

## Running Tests

```bash
pytest
```

## Architecture

- **Models**: SQLAlchemy ORM (replaced raw SQLite)
- **Services**: Business logic layer
- **Engine**: Event processing, guards, risk scoring
- **Controllers**: Flask blueprints
- **Middleware**: Auth, session validation, rate limiting
