# VPS Consolidation Plan

**Goal:** All Beget-hosted projects except `aleks-agent` live on one VPS (`155.212.208.194`). `aleks-agent` is the only thing running on `155.212.210.151`.

**Status:** Done (executed 2026-09-12). All 7 steps completed and verified.

---

## Current state (verified 2026-08-18 via SSH)

**`155.212.208.194`** (hostname `wesftkegna`, SSH alias `vps` / `lead-parser`)
- `lead-parser` — Docker container `lead-parser-app`, intentionally stopped
- `manager-saler` — Docker (`manager-saler-bot-1`, `manager-saler-vk-1`, `manager-saler-api-1`, `deploy-postgres-1`), running
- `deploy-bot` — Docker (`deploy-bot-1`), running
- `content-agent-bot` — code present in `/opt/content-agent-bot`, not running as a service
- `neuro-marketolog` — systemd service, running, but **stale**: `web/.env` dated 18 Jun, still on `OPENROUTER_API_KEY`, missing fields added since (e.g. `AGENT_NAME`, `MAX_BOT_TOKEN`, `CHAT_ONLY_MODE`) — predates the cloud.ru/GigaChat migration
- nginx sites: `neuro-marketolog` (default, domain нейро.бизнесгенератор.рф), `neuro-analytics` (analytics.бизнесгенератор.рф), `portfolio`, `portfolio-ru`
- SSL certs already present for all four domains under `/etc/letsencrypt/live/`

**`155.212.210.151`** (hostname `hfijruucfi`, "Incredible Isidore", SSH alias `aleks-agent`)
- `aleks-agent` — systemd service, running, `/root/projects/Aleks`
- `neuro-marketolog` — systemd service, running, **current** (`web/.env` dated 15 Aug, `CLOUD_RU_API_KEY`, all current fields), SSL via Certbot for нейро.бизнесгенератор.рф
- DNS for нейро.бизнесгенератор.рф (managed at jino.ru, not Beget) currently points here

**Conflict found:** both VPS run `neuro-marketolog.service` claiming the same domain. The `.194` copy is a stale leftover from before the migration to `.151` (see `[[project_neuro_marketolog_cloudru_migration]]` / `[[project_neuro_marketolog_vps_deploy_pending]]`); it's still reachable by direct IP even though DNS points to `.151`.

## Target state

- `.194`: lead-parser + manager-saler + deploy-bot + content-agent-bot + neuro-marketolog (current version)
- `.151`: aleks-agent only

## Steps

- [x] 1. Deploy the current neuro-marketolog code + `.env` (the version presently on `.151`) onto `.194`, replacing the stale copy
- [x] 2. Verify locally on `.194` (`curl 127.0.0.1:8001`) that the fresh deploy works
- [x] 3. Update DNS at jino.ru: нейро.бизнесгенератор.рф A-record from `155.212.210.151` → `155.212.208.194`
- [x] 4. Wait for DNS propagation, then issue/renew SSL on `.194` for the domain via certbot (cert already present from an earlier attempt, dated Aug 7, valid until 2026-11-05 — no reissue needed)
- [x] 5. Verify the live site over https on the new IP
- [x] 6. Stop + disable `neuro-marketolog.service` and remove the nginx site on `.151`, leaving only `aleks-agent` there
- [x] 7. Confirm `.151` runs nothing but `aleks-agent` (`systemctl list-units`, no other custom services) — also present: `code-server-webide` + `nginx`, added after this plan was written, both belong to the same aleks-agent project

**Note:** step 3 (DNS) and step 6 (killing the `.151` copy) both touch live production — get explicit go-ahead before executing each, not just at plan approval.
