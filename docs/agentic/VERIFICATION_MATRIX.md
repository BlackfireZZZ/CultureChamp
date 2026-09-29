# Change verification matrix

| Change | Minimum falsifying check | Required gate |
|---|---|---|
| Documentation | links, paths and commands exist | `git diff --check` + review |
| Backend domain/application | unit test for rule/use case | Ruff, mypy, backend pytest |
| HTTP API | success + error tests + schema compatibility | backend gate + smoke |
| SQL/repository | PostgreSQL integration test | backend gate + query plan when expensive |
| Alembic | clean-database upgrade and recovery plan | `alembic check` + Compose smoke |
| Frontend logic | closest Vitest/component test | lint + test + build |
| UI flow | happy/error/keyboard paths | frontend gate + e2e |
| ML data/model | schema/leakage/baseline checks | Ruff + mypy + pytest + eval |
| Compose/runtime | `docker compose config --quiet` | clean build + smoke |

Run the focused check first, then the full gate required by the nearest `AGENTS.md`
when that component and its gate exist. Until the new scaffold is built, check
documentation links and paths, then run `git diff --check` and review the diff.
