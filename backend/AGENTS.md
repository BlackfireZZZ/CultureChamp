# Backend: local rules

Root `AGENTS.md` is mandatory.

- Dependencies flow `api → application → domain`; infrastructure implements ports.
- Pydantic schemas, SQLAlchemy models and domain types remain separate.
- Handlers validate, invoke a use case and map results; no SQL/business rules in handlers.
- Database changes require a new Alembic migration.

```bash
make backend-check
```
