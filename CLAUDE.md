---
title: "colombia-open — CLAUDE.md"
description: >
  Punto de entrada para sesiones de Claude Code en colombia-open. Este
  proyecto vive de sesiones recurrentes, a veces con meses de distancia —
  este archivo debe bastar para retomar sin que David tenga que
  re-explicar el contexto.
category: ai-entrypoint
audience: [claude-code, ai-agent]
priority: critical
related_docs: [docs/roadmap/roadmap.md, docs/licenses/data_licenses.md, docs/brand/design-system.md, docs/troubleshooting/entorno-windows.md]
last_updated: 2026-10-17
---

# CLAUDE.md — colombia-open

> **colombia-open**: librería Python que distribuye datasets públicos de
> Colombia, curados, normalizados y validados. Pipeline: extract → derive
> → validate → write → catalog.

## La regla que domina todo lo demás: una fuente por fin de semana

**Nunca** implementes dos fuentes nuevas en la misma sesión, y **nunca**
dejes una fuente a medias (extractor sin validación, o validación sin
tests). Cada fuente se implementa de punta a punta — extractor + builder +
validación + registro + tests + docs — antes de tocar la siguiente.

Si estás retomando una sesión y no es obvio qué sigue: corre `/next-source`.
Lee `docs/roadmap/roadmap.md` primero — ahí está la tabla completa de fuentes mapeadas
(implementadas y no), con su dificultad de acceso. **No propongas agregar
más de una fuente candidata a la vez**, y no agregues fuentes nuevas a la
tabla de `docs/roadmap/roadmap.md` sin que te lo pidan — ese mapeo ya está hecho.

## Mapa de carpetas

```
src/
├── colombia_open/     # librería pública (pip install) — nunca importa de abajo
│   ├── datasets.py       # Dataset(StrEnum) — actualizar a mano al agregar fuente
│   └── data_manager.py   # descarga/cachea el bundle de GitHub Releases (SHA256)
├── extractors/   # uno por fuente — fetch + fallback + raw snapshot
├── builders/     # staging -> normalizado (parquet/json) + catálogo runtime
├── validation/   # reglas por dominio, funciones puras (nunca lanzan)
├── registry/     # DatasetSpec — qué datasets existen, esquema, licencia
└── build_pipeline.py   # orquestador: `python -m src.build_pipeline` == `make build`

data/
├── raw/        # snapshots crudos, write-once
├── staging/    # CSV normalizado + metadata.json, un par por extractor
├── normalized/ # parquet/json finales + dataset_catalog.json (lo que lee la lib pública)
└── registry/   # datasets.json — fuente de verdad estática (a mano)

tests/        # un archivo por módulo de src/, misma estructura
scripts/      # doctor/verify/bundle — ver Makefile
docs/datasets/{name}.md   # un doc por dataset publicado
```

## Comandos

```bash
make bootstrap    # una vez: crea .venv con uv, instala extras pipeline+dev
make build        # extract -> normalize -> validate -> data/normalized/
make test         # pytest
make lint         # ruff check
make format-check # ruff format --check
make typecheck    # mypy
make sec          # bandit
make audit        # pip-audit
make check        # build + verify + test + lint + format-check + typecheck + sec
make doctor       # gates anti-drift (hoy: check_validation_registration.py)
```

> **Entorno Windows**: usa `uv venv --python 3.11 .venv` (no 3.12/3.14 —
> hay bugs conocidos de wheel/OpenSSL). Detalle y errores SSL propios de
> tu máquina → `docs/troubleshooting/entorno-windows.md` +
> `CLAUDE.local.md` (no versionado).

## Stack

Python 3.11+, Hatchling, Polars/PyArrow como core de datos. Extras
opcionales: `pipeline` (duckdb, pandas, openpyxl, tenacity, structlog),
`scraping` (curl_cffi, beautifulsoup4 — para fuentes sin API/descarga
directa), `geo` (geopandas, shapely), `validation` (frictionless), `mcp`.
Dev: pytest, mypy (strict), ruff, bandit, pip-audit, pre-commit.

## Reglas duras (no negociables)

1. **Nunca fabricar datos si una fuente falla al extraer.** Un extractor
   puede caer a un fallback embebido mínimo para desarrollo offline, pero
   SIEMPRE con `source_mode="fallback"` — y la CI de publicación
   (`scripts/verify_pipeline.py --require-live`) rechaza cualquier dataset
   que no esté en `source_mode="live"`. Ver `.claude/rules/extractors.md`.
2. **Códigos administrativos (`cod_dpto`, `cod_mpio`) son siempre string de
   ancho fijo, nunca int.** Excel/Polars/DuckDB pierden el cero inicial
   silenciosamente si no fuerzas el tipo. Ver `.claude/rules/validation.md`.
3. **Toda columna normalizada se documenta en `docs/datasets/{name}.md`**
   — el esquema no vive solo en el código.
4. **Nunca remover el link a la fuente oficial.** Cada dataset en el
   catálogo lleva `source_url` y `source_name`; es lo que hace auditable
   la procedencia del dato.
5. **`data/raw/` es write-once.** Nunca se edita un snapshot después de
   escrito — es el rastro de auditoría de qué devolvió la fuente.
6. **La librería pública (`colombia_open/`) nunca importa de
   `extractors/`, `builders/` ni `validation/`.** Esos tienen deps
   pesadas (duckdb, pandas, geopandas) detrás del extra `pipeline` — el
   `pip install colombia-open` base debe seguir siendo liviano.
7. **Todo validador nuevo se registra en `src/validation/__init__.py`
   (`VALIDATORS`)** y pasa `make doctor` — un validador sin registrar se
   salta en silencio.
8. **Ante licencia ambigua o restrictiva: no publicar el dato, publicar
   solo la metadata y el link a la fuente.** Ver `docs/licenses/data_licenses.md`.
9. **No propongas ni implementes una fuente nueva sin verificar su
   endpoint/URL actual primero** (curl/fetch, no solo búsqueda web) — el
   mapeo de `docs/roadmap/roadmap.md` puede estar desactualizado.
10. **`site/index.html` (landing page) es código de marca, no un documento
    aparte.** Usa solo los tokens de `site/styles.css`/`docs/brand/design-system.md`
    — nunca un color o fuente hardcodeada nueva. Al agregar una fuente,
    actualiza también la tarjeta en `#catalogo` y la fila en `#roadmap` de
    `site/index.html`, no solo los docs — la página pública no debe quedar
    desincronizada del roadmap real. **Todo lo que se publica a GitHub
    Pages vive dentro de `site/`** — nada de HTML/CSS de la web en la raíz
    del repo (la raíz es del paquete Python).

## Agregar una fuente nueva

1. `/next-source` (lee `docs/roadmap/roadmap.md`, propone la candidata de menor
   dificultad, arranca la skill) — o manualmente:
2. Verifica el endpoint/URL actual de la fuente candidata.
3. Usa la skill `.claude/skills/new-source/SKILL.md` con el nombre de la
   fuente y su URL — genera extractor + entrada de builder + validador +
   entrada de registro + tests base.
4. Corre `make check` — todo verde antes de considerar la fuente lista.
5. Documenta en `docs/datasets/{name}.md` y marca la fila en `docs/roadmap/roadmap.md`.
6. Agrega el dataset al enum `src/colombia_open/datasets.py::Dataset`.

## Dónde ir según tu tarea

| Quiero... | Ir a |
|---|---|
| Saber qué fuentes existen/faltan | `docs/roadmap/roadmap.md` |
| Agregar una fuente | Esta sección + `/next-source` + skill `new-source` |
| Entender el contrato de un extractor | `.claude/rules/extractors.md` |
| Entender qué significa "validado" | `.claude/rules/validation.md` |
| Ver el estado legal de un dataset | `docs/licenses/data_licenses.md` |
| Entender la API pública | `README.md` sección "Uso" + `src/colombia_open/core.py` |
| Revisar calidad de datos antes de mergear | agente `.claude/agents/data-quality-reviewer.md` |
| Tocar la landing page o la marca | `docs/brand/design-system.md` (tokens) + `site/index.html`/`site/styles.css` (implementación) |
| Cortar o versionar un release | `.claude/rules/releases.md` |
| Revisar PRs/issues de colaboradores externos | `.github/CONTRIBUTING.md` (flujo, Conventional Commits, política IA) |
| Entender/tocar el servidor MCP | `docs/mcp.md` + `src/colombia_open/mcp_server.py` |
