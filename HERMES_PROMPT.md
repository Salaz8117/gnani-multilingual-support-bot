# Hermes Task: Fix Remaining Repo Issues and Push to GitHub

You are working in the repository `Salaz8117/gnani-multilingual-support-bot` (local clone at `C:\Users\acer\gnani-bot`). A prior review round already hardened the app code (CORS, base64 validation, LLM JSON parsing, immutable session history, timezone-aware timestamps) and opened PR #1 against `master`. Your job is the SECOND pass: fix the infrastructure, packaging, and configuration defects listed below, verify each fix, then push everything to GitHub.

Work on a fresh branch `fix/hermes-pass2` created from `origin/master` (the canonical default branch). Do NOT force-push. Commit with Conventional Commits messages (`fix:` / `chore:` / `docs:`), one logical change per commit where practical.

## Issue list (fix all)

### 1. Missing LICENSE
`README.md` references a license but no LICENSE file exists at repo root.
- Add an MIT LICENSE file with copyright holder `Salaz8117` and year 2026.

### 2. pyproject.toml vs requirements.txt version conflict
`requirements.txt` declares newer minimums (fastapi>=0.115.0, pydantic>=2.9.0, httpx>=0.28.0, gradio>=5.0.0, ...) while `pyproject.toml` pins old exact versions (fastapi==0.110.1, pydantic==2.7.1, httpx==0.27.0, gradio==4.44.0, ...). Installing via either path yields different dependency graphs.
- Align both files on ONE consistent set of ranges. Prefer flexible lower bounds matching `requirements.txt`; drop hard `==` pins except where reproducibility matters (use `>=,<` ranges).
- Make `requirements.txt` and `pyproject.toml [project.dependencies]` semantically identical, or have `requirements.txt` simply delegate (`-e .`). Pick one approach and document it in README.

### 3. Python 3.14 incompatibility (numpy/librosa build failures)
`pyproject.toml` pins `numpy>=1.26.0,<2.0.0` and `librosa==0.10.2`. Both fail to build from source on Python 3.14 (no wheels).
- Bump numpy to `>=2.1` (has 3.14 wheels) and librosa to the latest release supporting numpy 2.x (>=0.11 if available, else remove the pin and note the constraint).
- Keep Dockerfile on python:3.11-slim (that is fine); ensure `requires-python` in pyproject.toml matches what is actually tested (>=3.10,<3.14 is honest if 3.14 isn't supported yet — but try to support it first).

### 4. requirements.txt missing librosa
`app/utils/audio.py` lazily imports `librosa` in `load_audio()` (line ~31) and `normalize_audio()` (line ~107), but `librosa` is absent from `requirements.txt` (it exists only in pyproject.toml). Anyone installing via `pip install -r requirements.txt` gets a broken resample path.
- Add `librosa` to `requirements.txt` with the same range as pyproject.toml.

### 5. pytest-asyncio misconfiguration
Tests use `@pytest.mark.asyncio` decorators AND pyproject.toml sets `asyncio_mode = "auto"` — redundant, and collection emits `PytestUnknownMarkWarning` when pytest-asyncio isn't installed (which happens with `pip install -r requirements.txt` alone... actually pytest-asyncio IS listed; the real problem is the warnings appear because tests currently error at import time due to issue 6).
- With `asyncio_mode = "auto"`, REMOVE the explicit `@pytest.mark.asyncio` decorators from `tests/test_pipeline.py`, `tests/test_evon.py`, `tests/test_prisma.py`, `tests/test_timbre.py` (they're noise under auto mode).
- Verify `pytest tests/ --collect-only` succeeds cleanly after fixing issue 6.

### 6. Test collection fails: structlog/pydub/gradio import chain
`tests/test_pipeline.py` imports `app.pipelines.support_bot` → `structlog`; `app.utils.audio` (imported transitively) → `pydub`. In a bare `pip install -r requirements.txt` environment these ARE declared, so they should install — but the current local env lacks them. Confirm a clean venv + `pip install -r requirements.txt` makes `pytest tests/` pass. If any transitive import still breaks collection, guard it or move heavy audio deps behind lazy imports inside functions.

### 7. .env.example missing CORS_ORIGINS
`app/core/config.py` defines `cors_origins` (line ~54) consumed by `app/main.py` (line ~100, `get_settings().cors_origins_list`). `.env.example` has no `CORS_ORIGINS` entry, so new users get the code default silently instead of knowing the knob exists.
- Add to `.env.example`:
```
# CORS allowed origins (comma-separated). Never use "*" together with credentials.
CORS_ORIGINS=http://localhost:3000,http://localhost:7860
```

### 8. Demo scenario audio files don't exist
`app/demo.py` wires scenario buttons to `assets/sample_audio/hinglish_refund_noisy.wav`, `tamil_complaint.wav`, `english_order_status.wav`, `bengali_technical.wav` (lines ~333-338). `app/main.py` `/api/v1/demo/scenarios` advertises the same paths. `assets/sample_audio/` contains ONLY `README.md` — clicking any scenario button raises FileNotFoundError (caught, surfaced as an error box, but the advertised demo flow is broken).
- Either generate the four WAV files (e.g. extend `scripts/generate_demo.py` to synthesize placeholder silence/tone WAVs at those exact filenames and commit them, keeping each < 1 MB), or update demo.py + main.py scenarios to point at generated-at-runtime temp files. Generating and committing small placeholder WAVs is preferred so the README's "60-second demo" works out of the box.

### 9. Duplicate/divergent branches on origin
Remote has three branches: `master` (canonical, HEAD), `main` (leftover from an earlier push, sha 76772f8), and `fix/review-issues` (PR #1 source). After merging/pass-2 work:
- Ensure all fixes land relative to `master`.
- Delete the stale `main` branch on the remote once you've confirmed nothing depends on it: `git push origin --delete main`. Leave `fix/review-issues` until PR #1 is merged or closed.

## Verification gate (run before pushing)

1. `python -m compileall -q app scripts tests` → exit 0
2. Fresh venv: `python -m venv .venv && .venv/bin/pip install -r requirements.txt` (or `pip install -e ".[dev]"` — whichever layout you chose in issue 2) → success on Python 3.11 AND (attempt) 3.14
3. `pytest tests/ -q` → all green, zero warnings about unknown marks
4. `python -c "from app.main import app; print('OK')"` → OK
5. `uvicorn app.main:app --port 8000` boots without GNANI_API_KEY failing hard? No — it SHOULD raise ConfigurationError; verify that's the behavior and it's documented.
6. Launch `python app/demo.py`, click each of the 4 scenario buttons, confirm none errors (issue 8).

## Delivery

- Push the branch (`git push -u origin fix/hermes-pass2`).
- Open a PR against `master` titled `fix: resolve packaging, licensing, and config gaps (pass 2)` with a checklist mirroring the nine items above, marking each DONE with the command/output that proves it.
- If any item cannot be completed (e.g. upstream wheel availability blocks item 3), say so explicitly in the PR body with the evidence rather than skipping silently.