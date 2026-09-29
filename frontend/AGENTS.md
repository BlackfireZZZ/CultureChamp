# Frontend: local rules

Root `AGENTS.md` and `DESIGN.md` are mandatory.

- HTTP access goes through `src/api`; feature components never call `fetch` directly.
- Server state lives in query hooks; transport types stay at the API boundary.
- `src/components/ui` contains primitives without product logic.
- Every flow covers loading, empty, error, stale/success and keyboard access.

```bash
cd frontend
npm run lint
npm run test -- --run
npm run build
```
