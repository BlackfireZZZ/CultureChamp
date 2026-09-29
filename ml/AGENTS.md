# ML: local rules

Root `AGENTS.md` is mandatory.

- Record objective, baseline, metrics, slices and threshold before an experiment.
- Dataset manifests include origin, consent/licensing, version, geography, time range and leakage controls.
- Retrieval/AI evaluation covers source attribution, unsupported claims, uncertainty and regional slices.
- Image/audio matching reports confidence and never turns a probable match into a fact.
- Training and batch code must not be imported by the online backend worker.

```bash
uv run --package culturechamp-ml ruff check ml
uv run --package culturechamp-ml mypy ml/src
uv run --package culturechamp-ml pytest ml/tests
```
