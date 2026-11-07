<img src="site/assets/brand/mark-indigo.svg" alt="colombia-open" width="96">

# <img src="https://flagcdn.com/co.svg" alt="Colombia" width="28" valign="middle"> Colombia Open

[![Pipeline Check](https://github.com/davidcasr/colombia-open/actions/workflows/pipeline-check.yml/badge.svg)](https://github.com/davidcasr/colombia-open/actions/workflows/pipeline-check.yml)
[![PyPI](https://img.shields.io/pypi/v/colombia-open)](https://pypi.org/project/colombia-open/)
[![Python](https://img.shields.io/pypi/pyversions/colombia-open)](https://pypi.org/project/colombia-open/)
[![License](https://img.shields.io/github/license/davidcasr/colombia-open)](LICENSE)
[![Datasets](https://img.shields.io/badge/datasets-12-success)](#datasets-disponibles)

Datasets públicos de Colombia, **curados, normalizados y validados**, para
que cualquiera los use desde Python sin lidiar con los portales, APIs y
Excels inconsistentes de cada institución oficial.

```python
from colombia_open import ColombiaOpen

hub = ColombiaOpen()
municipios = hub.load_polars("municipios")
departamentos = hub.load_polars("departamentos")
```

> **Proyecto en MVP activo.** Once fuentes están implementadas de punta a
> punta (DIVIPOLA: departamentos + municipios, DANE; geometría municipal,
> MGN/HDX; demografía: proyecciones de población, DANE; educación:
> establecimientos y Saber 11, MEN/ICFES; seguridad: hurto a personas,
> lesiones personales e hurto a residencias/comercio, Policía;
> infraestructura: puntos de interés urbanos, OpenStreetMap;
> macroeconomía: TRM, Superfinanciera; y calidad del aire, IDEAM).
> Publicado en [PyPI](https://pypi.org/project/colombia-open/)
> (`pip install colombia-open`), con
> [GitHub Releases](https://github.com/davidcasr/colombia-open/releases)
> para el bundle de datos y landing page en vivo en
> [davidcasr.com/colombia-open](https://davidcasr.com/colombia-open/) —
> ver [Estado del proyecto](#estado-del-proyecto).

## Por qué existe

Los datos públicos de Colombia existen, son abiertos, y están dispersos en
decenas de portales con formatos, convenciones de código y calidad de API
distintas (DANE, IDEAM, ICFES, DNP, Banco de la República, XM...). El trabajo
real casi nunca es "¿existe el dato?" sino "¿cuánto tiempo me toma
normalizarlo, validarlo, y confiar en que no tiene errores silenciosos
(ej. un código de municipio que perdió el cero inicial en Excel)?"

`colombia-open` hace ese trabajo una vez, por fuente, y lo distribuye como
tablas [Polars](https://pola.rs)/Parquet listas para usar — con su fuente
oficial, licencia y fecha de actualización siempre visibles.

## Instalación

```bash
pip install colombia-open
```

Para correr el pipeline localmente (extraer datos en vivo, no solo leerlos):

```bash
git clone https://github.com/davidcasr/colombia-open.git
cd colombia-open
make bootstrap   # crea .venv e instala con extras pipeline+dev
make build       # extract -> normalize -> validate -> data/normalized/
make test
```

## Uso

```python
from colombia_open import ColombiaOpen

hub = ColombiaOpen()

hub.list_datasets()
# ["departamentos", "municipios", "municipios_geometria", "demografia",
#  "educacion_establecimientos", "educacion_saber11",
#  "delincuencia_hurto_personas", "delincuencia_lesiones_personales",
#  "delincuencia_hurto_modalidades", "infraestructura_poi",
#  "macroeconomia_trm", "calidad_aire"]

municipios = hub.load_polars("municipios")
municipios.filter(municipios["cod_dpto"] == "05")  # municipios de Antioquia

hub.resolve_municipios(["Medellín", "cali", "BOGOTA"])
# resuelve nombres a código DIVIPOLA, sin fuzzy matching (coincidencia exacta
# normalizada: sin tildes, minúsculas)

hub.cross_view(["municipios", "departamentos"], on="cod_dpto")
# join listo entre dos datasets que comparten una clave territorial

hub.provenance("municipios")
# {"source_name": "DANE — DIVIPOLA...", "source_url": "...", "source_mode": "live", ...}
```

CLI equivalente:

```bash
colombia-open list
colombia-open show municipios
colombia-open path municipios --output parquet
colombia-open example municipios --kind python
colombia-open validate municipios
```

## Datasets disponibles

| Dataset         | Descripción                                                                      | Fuente                 | Filas | Licencia     |
| --------------- | -------------------------------------------------------------------------------- | ---------------------- | ----- | ------------ |
| `departamentos` | Departamentos: código DIVIPOLA (2 dígitos) + nombre                              | DANE, vía datos.gov.co | 33    | CC BY-SA 4.0 |
| `municipios`    | Municipios: código DIVIPOLA (5 dígitos), nombre, departamento, centroide lon/lat | DANE, vía datos.gov.co | ~1122 | CC BY-SA 4.0 |
| `municipios_geometria` | Geometría de polígonos municipales (MGN), simplificada, con área geodésica | DANE (MGN), vía HDX | ~1122 | CC BY-IGO 3.0 |
| `demografia`    | Proyecciones de población municipal por área geográfica, 2018-2042              | DANE (descarga directa) | ~84225 | Términos DANE (público) |
| `educacion_establecimientos` | Directorio único de establecimientos educativos, 2015-2025            | MEN, vía datos.gov.co  | ~606206 | CC BY-SA 4.0 |
| `educacion_saber11` | Resultados Saber 11 agregados por establecimiento y periodo, 2010-2022 | ICFES, vía datos.gov.co | ~105110 | CC BY-SA 4.0 |
| `delincuencia_hurto_personas` | Víctimas de hurto a personas por municipio y día, 2003 a la fecha      | MinDefensa / Policía, vía datos.gov.co | ~650835 | CC BY-SA 4.0 |
| `delincuencia_lesiones_personales` | Víctimas de lesiones personales (incl. tránsito) por municipio, día, conducta, arma, género y edad, 2010 a la fecha | Policía Nacional, vía datos.gov.co | ~1377323 | CC BY-SA 4.0 |
| `delincuencia_hurto_modalidades` | Víctimas de hurto a residencias y entidades comerciales por municipio, día, arma, género y edad, 2010 a la fecha | Policía Nacional, vía datos.gov.co | ~397361 | CC BY-SA 4.0 |
| `infraestructura_poi` | Puntos de interés urbanos (salud, educación, seguridad, finanzas, religión, gobierno, transporte, comercio) por municipio | OpenStreetMap, vía Geofabrik | ~58046 | ODbL 1.0 |
| `macroeconomia_trm` | Tasa de Cambio Representativa del Mercado (COP/USD) diaria, 1991 a la fecha | Superintendencia Financiera, vía datos.gov.co | ~8372 | CC BY-SA 4.0 |
| `calidad_aire` | Contaminantes del Índice de Calidad del Aire (PM10, PM2.5, SO2, O3, NO2, CO) por estación, 2011 a la fecha | IDEAM, vía datos.gov.co | ~8985 | CC BY-SA 4.0 |

Ver `docs/roadmap/roadmap.md` para las ~14 fuentes mapeadas (implementadas y
pendientes) y `docs/licenses/data_licenses.md` para el detalle legal de cada una.

## Instalación con extras

| Extra        | Para qué                                                  | Incluye                                       |
| ------------ | --------------------------------------------------------- | --------------------------------------------- |
| (base)       | Solo **leer** datos ya publicados                         | polars, pyarrow, requests, platformdirs       |
| `pipeline`   | Correr extract→build→validate localmente                  | duckdb, pandas, openpyxl, tenacity, structlog |
| `scraping`   | Fuentes sin API/descarga directa (entorno aparte)         | curl_cffi, beautifulsoup4, defusedxml         |
| `geo`        | Correr los extractores de `municipios_geometria`/`infraestructura_poi` localmente (leer los datasets publicados no lo necesita) | geopandas, shapely, osmium |
| `validation` | Validación estricta de esquema (Frictionless)             | frictionless                                  |
| `mcp`        | Servidor MCP para que agentes de IA consulten el catálogo | mcp                                           |

```bash
pip install "colombia-open[pipeline]"
```

## Servidor MCP

```bash
pip install "colombia-open[mcp]"
colombia-open mcp   # stdio — agregalo como comando en tu cliente MCP
```

Config típica de cliente MCP (Claude Desktop, Claude Code, etc.):

```json
{
  "mcpServers": {
    "colombia-open": { "command": "colombia-open", "args": ["mcp"] }
  }
}
```

Expone 3 tools: `list_datasets()`, `describe_dataset(dataset)` (metadata +
esquema de columnas) y `query(sql, limit=None)` — SQL de solo lectura
contra todos los datasets como tablas nombradas, con JOIN entre datasets en
una sola query. Las filas siempre se limitan automáticamente (hasta 1000)
para no volcarle a un agente un dataset de 600k filas crudo. Detalle
completo, incluida la validación de seguridad del SQL, en `docs/mcp.md`.

## Filosofía: una fuente por fin de semana

Este proyecto **no** se construye de golpe. Cada fuente nueva se implementa
de punta a punta (extractor + builder + validación + registro + tests +
docs) antes de empezar la siguiente. El resto de las fuentes candidatas
quedan mapeadas en `docs/roadmap/roadmap.md` con su dificultad de acceso, sin
implementar, hasta que les toque su turno.

La razón de ingeniería: la prioridad #1 no es "cuántas fuentes tenemos" sino
"qué tan fácil es agregar la fuente número N+1 sin releer todo el código
cada vez" — por eso existe la skill `.claude/skills/new-source/` y el
comando `/next-source`. Ver `CLAUDE.md` para el detalle completo.

## Arquitectura

```
src/
├── colombia_open/     # librería pública (pip install), deps livianas
├── extractors/        # uno por fuente institucional — fetch + fallback + raw snapshot
├── builders/          # staging -> normalizado (parquet/json) + catálogo
├── validation/        # reglas por dominio, funciones puras
└── registry/          # qué datasets existen, su esquema y su licencia

data/
├── raw/           # snapshots crudos, write-once (no se edita después)
├── staging/       # CSV normalizado + metadata.json por extractor
├── normalized/    # parquet/json finales + dataset_catalog.json (lo que lee la librería)
└── registry/      # datasets.json — fuente de verdad estática del registro
```

La librería pública (`colombia_open/`) nunca importa código de pipeline
(`extractors/`, `builders/`, `validation/`) — así `pip install colombia-open`
se mantiene liviano. El primer uso descarga y cachea el bundle de datos
publicado en GitHub Releases (con verificación SHA256); en desarrollo, lee
directamente `data/normalized/` si ya corriste `make build`.

## Estado del proyecto

- ✅ Patrón extractor/builder/validación/registro probado con once
  fuentes (DIVIPOLA, geometría MGN vía HDX, demografía, dos de educación,
  tres de delincuencia, POI de OpenStreetMap, TRM y calidad del aire) de
  dominios distintos (API Socrata pequeña, descarga directa de Excel, API
  Socrata grande y paginada —incluida una de 7.1M filas con paginación por
  keyset—, shapefile geoespacial, extracto `.osm.pbf` con
  geoprocesamiento).
- ✅ [GitHub Releases](https://github.com/davidcasr/colombia-open/releases)
  publicados (último: `v0.12.0`, bundle de datos con SHA256, incluye las
  once fuentes) — `ColombiaOpen()` descarga y cachea el bundle
  automáticamente sin tener que correr el pipeline localmente (ver
  `data_manager.py`). Convención de versionado: `.claude/rules/releases.md`.
- ✅ **Publicado en [PyPI](https://pypi.org/project/colombia-open/)**
  (`pip install colombia-open`, trusted publishing vía
  `.github/workflows/publish.yml`, sin token almacenado) — verificado
  end-to-end el 2026-10-18 instalando desde PyPI real en un venv limpio: los
  4 datasets cargan correctamente.
- ✅ Servidor MCP (desde `v0.4.0`, extra `mcp`): agentes de IA pueden
  listar, describir y consultar con SQL de solo lectura todo el catálogo
  vía `colombia-open mcp` — ver [Servidor MCP](#servidor-mcp) y
  `docs/mcp.md`.
- ✅ Landing page (`site/`, ver `docs/brand/design-system.md`) deployada en
  [davidcasr.com/colombia-open](https://davidcasr.com/colombia-open/).
- Ver `docs/roadmap/roadmap.md` para qué sigue.

## Legal

El código es MIT (`LICENSE`). Cada dataset conserva la licencia de su fuente
original — ver `docs/licenses/data_licenses.md` antes de redistribuir cualquier dataset
fuera de este paquete.

## Contribuir

¡Las contribuciones son bienvenidas! Lee la
[guía de contribución](.github/CONTRIBUTING.md) antes de abrir una PR: todo
cambio empieza en un issue, los títulos de PR siguen
[Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/) y
`make check` debe pasar en verde. Al participar aceptas el
[Código de Conducta](.github/CODE_OF_CONDUCT.md). Para temas de seguridad,
ver [SECURITY.md](.github/SECURITY.md).

Hecho por [David Castro](https://github.com/davidcasr). El flujo de trabajo
está pensado para sesiones de Claude Code recurrentes — ver `CLAUDE.md` si
vas a contribuir con un agente de IA.
