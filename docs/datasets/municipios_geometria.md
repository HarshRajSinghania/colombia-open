# municipios_geometria

Geometría de polígonos municipales — segunda iteración de `divipola` /
`municipios` (que solo trae centroide, no polígono). Un polígono (o
multipolígono) por municipio, con su área geodésica.

- **Fuente**: IGAC (Instituto Geográfico Agustín Codazzi), vía servicio
  ArcGIS REST "MunicipiosSNR" de la Superintendencia de Notariado y
  Registro (SNR):
  <https://services2.arcgis.com/RVvWzU3lgJISqdke/arcgis/rest/services/MunicipiosSNR/FeatureServer/0>.
- **Licencia**: CC BY 4.0 — ver `docs/licenses/data_licenses.md`.
- **Extractor**: `src/extractors/municipios_geometria_extractor.py`.
- **Filas esperadas**: ~1122 (confirmado en vivo el 2026-11-05).
- **Migrado desde HDX el 2026-11-05**: el recurso anterior
  (`data.humdata.org/dataset/cod-ab-col`) empezó a devolver un reto de AWS
  WAF a cualquier cliente no-navegador en vez del shapefile real — ver
  `git log` de `src/extractors/municipios_geometria_extractor.py` y el
  docstring del módulo para el detalle completo del diagnóstico.

## Esquema

| Columna | Tipo | Descripción |
|---|---|---|
| `cod_dpto` | string (2 dígitos) | Código DIVIPOLA de departamento (derivado de `ADM1_PCODE`). **Nunca convertir a int.** |
| `cod_mpio` | string (5 dígitos) | Código DIVIPOLA de municipio (derivado de `ADM2_PCODE`) — join key hacia `municipios`. **Nunca convertir a int.** |
| `geom_type` | string | `"Polygon"` (1113 municipios) o `"MultiPolygon"` (9 municipios con islas o exclaves, ej. San Andrés). |
| `area_km2` | float | Área geodésica (`pyproj.Geod(ellps="WGS84")`), calculada sobre la geometría **original** antes de simplificar — no carga el error de la simplificación. |
| `geometry_wkt` | string | Polígono en formato WKT (Well-Known Text), EPSG:4326 (lon/lat, WGS84). **Simplificado** (tolerancia Douglas-Peucker 0.0005°, ~55m en el ecuador) y redondeado a 6 decimales — ver Limitaciones. |

Clave primaria: `cod_mpio` — única, validada en cada build.

## Uso

```python
import polars as pl
from colombia_open import ColombiaOpen
import shapely.wkt

hub = ColombiaOpen()
geometria = hub.load_polars("municipios_geometria")

# Parsear a geometría shapely/geopandas para análisis espacial
geometria = geometria.with_columns(
    pl.col("geometry_wkt").map_elements(shapely.wkt.loads, return_dtype=pl.Object).alias("geometry")
)

# Municipio más grande por área
geometria.sort("area_km2", descending=True).head(5)

# Densidad poblacional: join con demografia (población) y área
poblacion = (
    hub.load_polars("demografia")
    .filter((pl.col("area_geografica") == "Total") & (pl.col("anio") == 2024))
)
(
    hub.load_polars("municipios_geometria")
    .join(poblacion.select(["cod_mpio", "poblacion"]), on="cod_mpio")
    .with_columns((pl.col("poblacion") / pl.col("area_km2")).alias("densidad_hab_km2"))
    .sort("densidad_hab_km2", descending=True)
)

# Para mapas: convertir a GeoDataFrame (requiere el extra `geo`)
import geopandas as gpd
gdf = gpd.GeoDataFrame(
    geometria.to_pandas(),
    geometry=geometria["geometry_wkt"].map_elements(shapely.wkt.loads, return_dtype=pl.Object).to_pandas(),
    crs="EPSG:4326",
)
```

## Limitaciones conocidas

- **Geometría simplificada, no survey-grade.** El shapefile original del
  MGN tiene ~5.7 millones de vértices en total (perfecto para GIS,
  impráctico para una librería de propósito general). Se simplifica con
  tolerancia 0.0005° (~55m en el ecuador, Douglas-Peucker con
  `preserve_topology=True`) y se redondean las coordenadas a 6 decimales,
  reduciendo el tamaño en >90%. **No uses este dataset para análisis que
  requiera precisión catastral o deslinde de límites** — para eso, ve
  directo a la fuente del Geoportal DANE.
- **No incluye nombre de municipio.** `cod_mpio` es la única clave; haz
  join con `municipios` para el nombre, evitando mantener dos copias que
  puedan divergir entre fuentes (DANE/DIVIPOLA vs. MGN/HDX).
- **Vigencia de la cartografía fijada por el proceso de deslinde de cada
  entidad territorial**, no necesariamente la más reciente posible — el
  límite administrativo de un municipio cambia con poca frecuencia, así
  que el desfase esperado frente al DIVIPOLA vigente es mínimo (ver
  siguiente punto).
- **Posible discrepancia de `cod_mpio` con `municipios` (DIVIPOLA).** El
  validador reporta cualquier `cod_mpio` que no exista en `municipios`
  vigente como warning, no como error — mismo criterio que el resto de
  datasets que no son DIVIPOLA puro.
- **CRS fijo en EPSG:4326** (lon/lat, WGS84) — si necesitas un CRS
  proyectado (ej. para cálculos de distancia en metros), reproyecta tú
  mismo con `geopandas`.
