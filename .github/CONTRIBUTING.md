# Cómo contribuir a colombia-open

¡Gracias por querer aportar! `colombia-open` distribuye datasets públicos de
Colombia curados, normalizados y validados. Como lo que publicamos lo usan
otras personas para analizar datos reales, el proceso prioriza **procedencia
auditable y calidad** sobre velocidad.

Al participar aceptas el [Código de Conducta](CODE_OF_CONDUCT.md).

## Antes de escribir código: abre (o toma) un issue

Todo cambio no trivial empieza en un issue — así nadie trabaja dos veces en
lo mismo ni dedica un fin de semana a algo que no se va a mergear.

| Quiero... | Haz esto |
|---|---|
| Reportar un dato incorrecto o un extractor roto | Issue **🐛 Bug en un dataset o extractor** |
| Proponer una fuente de datos nueva | Issue **📊 Proponer una fuente** |
| Proponer una mejora a la librería / API | Issue **✨ Mejora** |
| Preguntar, discutir una idea | [Discussions](https://github.com/davidcasr/colombia-open/discussions) |
| Reportar una vulnerabilidad | **No** abras un issue — ver [SECURITY.md](SECURITY.md) |

**Para trabajar en un issue existente**, comenta "lo tomo" y espera a que el
mantenedor te lo asigne. Un issue asignado es de esa persona; si no hay
avance en ~2 semanas se libera para otra.

Los issues marcados `good first issue` son buenos para empezar.

### Fuentes de datos nuevas

El mapa de fuentes (implementadas y pendientes) está en
[`docs/roadmap/roadmap.md`](../docs/roadmap/roadmap.md). Reglas del proyecto:

- **Una fuente por PR, de punta a punta**: extractor + builder + validación +
  registro + tests + docs. No se aceptan fuentes a medias.
- **Verifica el endpoint antes de proponer** (`curl`, no solo una búsqueda
  web) — el roadmap puede estar desactualizado.
- **Licencia ambigua o restrictiva → no se publica el dato**, solo metadata
  y link a la fuente. Ver [`docs/licenses/data_licenses.md`](../docs/licenses/data_licenses.md).

## Entorno de desarrollo

Requisitos: Python 3.11+, [uv](https://docs.astral.sh/uv/) y `make`.

```bash
git clone https://github.com/<tu-usuario>/colombia-open.git
cd colombia-open
make bootstrap        # crea .venv con uv e instala extras pipeline + dev
pre-commit install    # ruff + chequeos antes de cada commit
```

> En Windows usa `uv venv --python 3.11 .venv` (no 3.12/3.14). Ver
> [`docs/troubleshooting/entorno-windows.md`](../docs/troubleshooting/entorno-windows.md).

## Flujo de trabajo

1. Haz **fork** del repo y crea una rama desde `main`:
   `git checkout -b feat/nombre-corto`.
2. Haz tus cambios. Antes de abrir la PR, todo en verde:

   ```bash
   make check    # build + verify + test + lint + format-check + typecheck + sec
   make doctor   # gates anti-drift (validadores registrados, etc.)
   ```

3. Abre la PR contra `main` y completa la plantilla. Enlaza el issue con
   `Closes #123`.
4. El CI corre en tu PR (la primera vez, el mantenedor tiene que aprobar que
   corra — es una protección anti-spam de GitHub, no algo personal).
5. Revisión → ajustes → **squash merge**. El título de tu PR será el commit
   en `main`.

## Convención de commits y títulos de PR

Usamos [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/).
**El título de la PR es obligatorio en este formato** (lo valida el CI);
los commits dentro de tu rama pueden ser libres porque se aplastan al mergear.

```
<tipo>(<alcance opcional>): <descripción en minúscula, imperativo>
```

| Tipo | Cuándo | Efecto en la versión |
|---|---|---|
| `feat` | Fuente/dataset nuevo, método nuevo en la API | MINOR |
| `fix` | Corrección en extractor/validador/builder sin cambiar esquema | PATCH |
| `docs` | Solo documentación | — |
| `test` | Solo tests | — |
| `refactor` | Cambio interno sin cambio de comportamiento | — |
| `perf` | Mejora de rendimiento | PATCH |
| `style` | Formato, landing page (estilos) | — |
| `ci` / `build` / `chore` | CI, empaquetado, mantenimiento | — |

Un cambio que rompe compatibilidad (renombrar/quitar una columna publicada,
cambiar una firma pública) lleva `!`: `feat!: renombrar cod_mun a cod_mpio`.

Ejemplos reales del historial:

```
feat: agregar calidad_aire (contaminantes ICA por estación, IDEAM)
fix: migrar municipios_geometria de HDX a ArcGIS (IGAC/SNR)
docs: actualizar conteo de fuentes/datasets en README
```

Detalle de versionado: [`.claude/rules/releases.md`](../.claude/rules/releases.md).

## Reglas duras (las revisa la PR)

Resumen de [`CLAUDE.md`](../CLAUDE.md) — léelo completo si vas a tocar el
pipeline:

1. **Nunca fabricar datos.** Si la fuente falla, el extractor cae a un
   fallback marcado `source_mode="fallback"`, que nunca se publica.
2. **`cod_dpto` / `cod_mpio` siempre string de ancho fijo** (2 y 5), nunca int.
3. **Toda columna normalizada se documenta** en `docs/datasets/{name}.md`.
4. **Nunca quitar `source_url` / `source_name`** de un dataset.
5. **`data/raw/` es write-once** — no se editan snapshots.
6. **`src/colombia_open/` no importa** de `extractors/`, `builders/` ni
   `validation/` — la librería pública debe seguir siendo liviana.
7. **Todo validador nuevo se registra** en `VALIDATORS` y pasa `make doctor`.

Contratos detallados:
[extractores](../.claude/rules/extractors.md) ·
[validación](../.claude/rules/validation.md).

## Contribuir con agentes de IA

El repo está preparado para trabajar con Claude Code (`CLAUDE.md`,
`.claude/rules/`, skills `/next-source` y `new-source`). **Las PRs hechas con
IA son bienvenidas**, con estas condiciones:

- Tú eres responsable del contenido: revisaste el diff y entiendes lo que
  cambia. "Lo generó el agente" no es respuesta a un comentario de revisión.
- `make check` pasa en tu máquina, no solo "debería pasar".
- Verificaste el endpoint de una fuente nueva tú mismo/a — no confíes en una
  URL que el modelo "recuerda".
- No abras PRs masivas o automáticas sin issue previo. Las PRs que parezcan
  generadas en lote sin revisión humana se cierran sin revisar.

## Qué NO hace falta en tu PR

- Bumpear `version` en `pyproject.toml` — lo hace el mantenedor al cortar el
  release.
- Disparar workflows de release o publicación a PyPI — son manuales y del
  mantenedor.

## Reconocimiento

Cada release menciona a quienes contribuyeron en sus notas. ¡Gracias!
