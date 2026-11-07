# RCA — RCC8_ENVIRONMENT not "on" in production (milton-propagate)

## Problem statement
Backend `enabled()` in `backend/rcc8_env/environment.py` checks `os.environ.get("RCC8_ENVIRONMENT") == "on"`. Repo `backend/.env` has `RCC8_ENVIRONMENT="on"` (committed before the latest deploy), but live `GET /api/health/memory` reports `rcc8.enabled=false`, i.e. prod does not see "on".

## Findings (evidence)

### (1) Did a second deploy build & roll out? Which commit is live?
YES — deploys ran after the `.env` change. `describe_deployment_state` shows 4 successful runs on this deployment:
- `d3e4bac1` initial — 2026-11-06 01:21
- `68c36314` redeploy — 2026-11-06 16:37
- `9b140319` redeploy — 2026-11-07 02:12
- `d25a7dcc` redeploy — 2026-11-07 02:42:53Z  ← **ACTIVE / LIVE**

Live image: `customers-app-3@sha256:7d32ee59...753abc49`, built by the most recent run `d25a7dcc`.

**The "same job_id" is a red herring.** `job_id` is the deployment-level job handle and is reused across every run (all 4 runs share `ae89f3d1-938f-4c2b-b5da-656ba9a17981`); each deploy gets a distinct `run_id`. The dispatcher returning the same job_id does NOT mean the deploy didn't run. (Note: the job_id the report cited, `42b156d2...`, does not match this deployment's job_id `ae89f3d1...` at all.) A fresh image was built and promoted at 02:42, so the `.env="on"` source IS in the live build.

### (2) What value does the prod pod have? Does prod env override backend/.env?
Prod pod has **`RCC8_ENVIRONMENT="off"`** — confirmed via `list_secrets`:
- `equals {"RCC8_ENVIRONMENT":"on"}` → `matches_expected: false`
- `equals {"RCC8_ENVIRONMENT":"off"}` → `matches_expected: true`
- `is_empty: false` (a value is set)

YES, production env overrides `backend/.env`: the process environment (the stored secret) takes precedence at runtime, so `enabled()` reads "off" regardless of the `.env` file baked into the image.

**Why it's stale:** `RCC8_ENVIRONMENT` is a user/custom secret. It was seeded "off" from the preview `.env` on the **initial** deploy (deploy #1, intended). On every redeploy after that, custom secrets are **carried forward from the previous production run**; the preview `.env` only ADDS new keys — it NEVER overwrites a key already stored in prod. So changing `backend/.env` from "off" → "on" had no effect: prod kept the original "off" value across all 3 redeploys.

### (3) What's needed for prod to get RCC8_ENVIRONMENT=on
The user must set it in **Deployment Panel → Secrets**: `RCC8_ENVIRONMENT=on`, then redeploy. Editing `backend/.env` alone will not fix it — the stored Secrets-tab value is authoritative and wins over the file.

## Memory / OOM / restarts since deploy #1
- Reported live: `rss_mb=334.5`, `peak_rss_mb=336.8` vs tier_0 **512MB** limit — healthy headroom.
- `get_pod_events` (active run, 24h): **no OOMKilled**, container `restart_count=0` on both pods.
- Transient 503 startup/readiness/liveness probe failures observed ~03:48 and ~03:53 (the 03:53 pod was an autoscale 1→2 scale-up). Both pods are now `ready`; the probe blips did not cross the restart threshold and are not memory-related.

## Classification
Config/secrets propagation issue — NOT a source or manifest bug. `backend/.env` is already correct; the live image already contains it. The blocker is the stale stored prod secret overriding it.
