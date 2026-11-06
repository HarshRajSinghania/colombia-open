---
title: "colombia-open — data_licenses.md"
description: >
  Licenciamiento y atribución por dataset. El código es MIT; los datos NO
  lo son — cada dataset conserva la licencia de su fuente original.
source_of_truth_for: [licensing, attribution, exclusion-policy, share-alike-handling]
related_docs: [CLAUDE.md, .claude/rules/extractors.md, docs/roadmap/roadmap.md]
last_updated: 2026-10-17
---

# Licenciamiento de datos

**Código**: MIT (`LICENSE`). **Datos**: cada fuente conserva su propia
licencia — no hay una licencia única para "los datos de colombia-open".

La fuente de verdad **machine-readable** del estado legal de cada dataset es
el campo `reuse_policy` dentro de `data/normalized/dataset_catalog.json`
(generado en build time) — este archivo es la referencia humana, no la
autoridad. Antes de redistribuir cualquier dataset fuera de este paquete,
corre:

```bash
colombia-open show <dataset>   # incluye reuse_policy completo
```

## Semáforo de licencias (criterio para aceptar una fuente nueva)

🟢 **`open-attribution`** — licencia abierta explícita (CC BY, CC BY-SA,
CC BY-IGO, ODbL, dominio público, Ley 1712 de 2014 sin restricción declarada). Se publica,
con atribución a la fuente siempre visible (nunca se remueve el link al
dato oficial — ver `.claude/rules/extractors.md`).

🟡 **`public-api-review-terms`** — API/descarga pública de una entidad
estatal colombiana, sin licencia explícita pero sin restricción de reuso
declarada (la Ley 1712/2014 de Transparencia establece que la información
pública es abierta por defecto salvo excepción expresa). Se publica solo
tras revisar que no haya una excepción aplicable.

🔴 **`restricted`** — términos restrictivos, ambiguos, o requiere
autenticación/convenio. **Se excluye del bundle público.** Regla por
defecto ante la duda: *no redistribuir el dato — publicar solo la
metadata y el link a la fuente original.*

## Share-alike (CC BY-SA): qué implica

Un dataset CC BY-SA (share-alike) puede redistribuirse, pero cualquier
redistribución de **ese dataset específico** debe mantenerse bajo la misma
licencia y atribución. Esto NO afecta la licencia del código (MIT) ni de
datasets con licencia distinta — si en el futuro se mezclan fuentes con
licencias incompatibles (ej. una share-alike y una CC BY simple) en una
tabla derivada, esa tabla derivada se mantiene separada y documentada bajo
la licencia más restrictiva de sus insumos, en vez de heredar silenciosamente
la más permisiva (segregar por familia de licencia, no mezclar y heredar la
más permisiva).

## Datasets actuales

| Dataset | Fuente | Licencia | Atribución requerida | Redistribuible |
|---|---|---|---|---|
| `departamentos` | DANE, vía datos.gov.co (`gdxc-w37w`) | CC BY-SA 4.0 | Sí — "DANE" | Sí, bajo CC BY-SA 4.0 |
| `municipios` | DANE, vía datos.gov.co (`gdxc-w37w`) | CC BY-SA 4.0 | Sí — "DANE" | Sí, bajo CC BY-SA 4.0 |
| `demografia` | DANE, descarga directa (dane.gov.co, PPED) | Sin CC explícito — términos de uso del DANE (`public-api-review-terms`) | Sí — "Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co" | Sí, bajo la presunción de apertura de la Ley 1712/2014 — ver nota abajo |
| `educacion_establecimientos` | MEN, vía datos.gov.co (`cfw5-qzt5`) | CC BY-SA 4.0 | Sí — "MinEducación" | Sí, bajo CC BY-SA 4.0 |
| `delincuencia_hurto_personas` | MinDefensa / Policía Nacional, vía datos.gov.co (`4rxi-8m8d`) | CC BY-SA 4.0 | Sí — "Ministerio de Defensa Nacional" | Sí, bajo CC BY-SA 4.0 |
| `delincuencia_lesiones_personales` | Policía Nacional (DIPON), vía datos.gov.co (`72sg-cybi`) | CC BY-SA 4.0 | Sí — "Dirección General de la Policía Nacional - DIPON" | Sí, bajo CC BY-SA 4.0 |
| `delincuencia_hurto_modalidades` | Policía Nacional (DIPON), vía datos.gov.co (`6sqw-8cg5`) | CC BY-SA 4.0 | Sí — "Dirección General de la Policía Nacional - DIPON" | Sí, bajo CC BY-SA 4.0 |
| `municipios_geometria` | IGAC, vía ArcGIS REST "MunicipiosSNR" (Superintendencia de Notariado y Registro) | CC BY 4.0 | Sí — "IGAC" | Sí, bajo CC BY 4.0 (sin exigir share-alike) |
| `infraestructura_poi` | OpenStreetMap, vía Geofabrik | ODbL 1.0 | Sí — "© OpenStreetMap contributors" | Sí, bajo ODbL 1.0 (share-alike de base de datos) |
| `educacion_saber11` | ICFES, vía datos.gov.co (`kgxf-xxbe`) | CC BY-SA 4.0 | Sí — "ICFES" | Sí, bajo CC BY-SA 4.0 |
| `macroeconomia_trm` | Superintendencia Financiera, vía datos.gov.co (`32sa-8pi3`) | CC BY-SA 4.0 | Sí — "Superintendencia Financiera" | Sí, bajo CC BY-SA 4.0 |
| `calidad_aire` | IDEAM, vía datos.gov.co (`kekd-7v7h`) | CC BY-SA 4.0 | Sí — "IDEAM" | Sí, bajo CC BY-SA 4.0 |

## Nota sobre `demografia` (public-api-review-terms)

A diferencia de `departamentos`/`municipios` (publicados en datos.gov.co
bajo CC BY-SA 4.0 explícito), `demografia` se descarga directamente de
dane.gov.co. Los términos de uso del DANE (revisados 2026-10-18)
autorizan expresamente "uso, aprovechamiento, transformación y análisis"
de la información con atribución obligatoria, pero no declaran ninguna
licencia Creative Commons ni mencionan explícitamente "redistribución".
Se publica bajo 🟡 `public-api-review-terms`: es información estadística
pública de una entidad estatal colombiana, sin restricción de reuso
declarada, bajo la presunción de apertura de la Ley 1712/2014 de
Transparencia. Si el DANE publicara en el futuro una licencia explícita
más restrictiva para este archivo, re-evaluar esta clasificación.

## Fuente permanentemente caída

Si una fuente deja de responder, el protocolo (antes de marcarla
deprecated) es: confirmar que la caída es permanente (esperar ~3 ciclos de
`source-urls.yml`), congelar el dataset en su última versión publicada, y
decidir si se mantiene como dataset histórico congelado (documentado como
tal) o se deprecia por completo. Nunca fabricar datos nuevos para
reemplazar una fuente caída.
