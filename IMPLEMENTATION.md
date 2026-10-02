# WildTrack completion status

WildTrack is a wildlife monitoring and advanced database concepts project. PostgreSQL/PostGIS is authoritative for animals, devices, zones, GPS observations, rules, and alerts. MongoDB stores delivered event documents. Neo4j Aura is a rebuildable projection used for movement network questions. Authentication, a demo mode, Hadoop/Hive, and a separate test database are outside the project scope.

## Phase checklist

- [x] 5.5 — Safe seed behavior, explicit API errors, data constraints, alert deduplication, and functional filters.
- [x] 6A — Compact map, route selection, hover/focus details, and collapsible map panels.
- [x] 6B — PostgreSQL persistence for zones, pins, preferences, and map simulation controls.
- [x] 6C — Temporal zone/rule versions, audit history, reliable event delivery, and operational summaries.
- [x] 7 — Incremental local Parquet archive for observation and alert facts.
- [x] 8 — Neo4j movement network for observed corridors and habitat disruption.
- [x] 9 — Analytics filters, temporal summary corrections, deployment blueprint, and demonstration documentation.

The code and deployment configuration for these phases are complete. External hosting is not provisioned by this repository: it requires the owner to connect a hosting account and supply production database credentials. The live visual workflow should be demonstrated with the steps in README.md.

## Database design and limits

- PostGIS uses spatial indexes, geography distances, boundary-inclusive `ST_Covers`, and deterministic zone overlap priority.
- PostgreSQL uses temporal version tables, window functions, JSONB ECA rules, unique constraints for active-alert deduplication, row locks for alert transitions, and database triggers for alert history and configuration audit.
- The transactional outbox commits with PostgreSQL changes, then retries idempotent delivery to MongoDB.
- Neo4j holds a generation-switched, rebuildable projection derived from PostgreSQL. It answers corridor and up-to-three-hop historical impact questions. A connection means successive visits to two zones by an animal within six hours; it does not claim an exact physical path or predict future movement.
- The local Parquet exporter claims source identifiers in a PostgreSQL ledger and resumes interrupted batches. It does not delete source records.
- Dwell time and distance are estimates from GPS fixes. Dwell uses a maximum 30-minute gap, is clipped to the chosen analytics range, and assigns a zone with the zone version valid at the first fix. Historical changes before version tracking began cannot be reconstructed.
- Simulation routes are generated software demonstration data, not verified wildlife telemetry.

## Phase 9 analytics behavior

The Analytics page defaults to the last seven calendar days. It supports custom date ranges up to 366 days and filters by elephant, tiger, deer, or all species. The date range is inclusive in the UI and sent to the API as timezone-qualified UTC bounds with an exclusive end. Alert trend results include dates with zero alerts. Distance includes a preceding observation just before the range when it forms a valid consecutive fix within 30 minutes. Dwell is clipped at both selected boundaries. The page links directly to Movement Network for graph-based corridor and disruption analysis.

The backend runs dashboard aggregates in one repeatable-read, read-only transaction so the charts describe a consistent snapshot. `GET /api/v1/analytics` accepts `start_time`, `end_time`, and `species` query parameters. Invalid, timezone-free, reversed, longer-than-366-day ranges and unsupported species are rejected.

## Run and demonstrate

Follow the setup commands in README.md. Use the project's `backend/venv` Python executable; system Python may have incompatible FastAPI/Pydantic versions. Migrations are applied explicitly. Seed scripts insert missing records only and must not be used as reset commands.

For a short demonstration, start the simulator on Live Monitor, watch the five corridor animals cross a zone boundary in about 30–45 seconds, then pause it. Open Analytics to select dates and species. Open Movement Network to refresh a stale graph projection, filter observed connections, select a corridor to inspect its contributors, and select a zone to inspect its historical multi-hop impact. Check the Live Monitor Status tab for alerts and outbox delivery state. README.md contains the full walkthrough and the Phase 7 archive commands.

## Deployment

`render.yaml` defines a FastAPI backend and static Vite frontend. It is a deploy-ready blueprint, not an active deployment. Before use, configure PostgreSQL/PostGIS, MongoDB, and optional Neo4j Aura credentials as server-side environment variables. Apply migrations from a trusted environment before directing the backend at a production database. Update CORS and API URLs if the hosting provider assigns different service domains. Never place database secrets in `VITE_` variables.

## Validation and remaining owner actions

The repository includes frontend contract tests and backend pure/mocked checks. Optional existing-database checks are read-only and gated by `WILDTRACK_READONLY_CHECKS=1`; they do not seed, reset, resolve alerts, or start the simulator. Previous phase notes record that the Aura projection and Parquet archive were checked against the configured project data. Do not run application/database checks against production without reviewing their read-only behavior first.

The owner still needs to connect Render (or another host), supply its production secrets, and perform a browser walkthrough after starting the services. Those account-specific steps cannot be completed from source code alone.
