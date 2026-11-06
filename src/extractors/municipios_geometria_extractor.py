"""Extractor de geometría de polígonos municipales (MGN/IGAC), vía ArcGIS
REST de la Superintendencia de Notariado y Registro (SNR).

Segunda iteración de `divipola` (ver docs/roadmap/roadmap.md, sección "Por
qué geografía fue primero"): agrega los polígonos que `divipola`/
`municipios` no incluye (solo centroide).

Fuente primaria: servicio ArcGIS REST "MunicipiosSNR", publicado por IGAC
(cuenta `antonio.moyano_IGAC_OIT`) en la organización ArcGIS Online de la
Superintendencia de Notariado y Registro (SNR), sobre cartografía del
Instituto Geográfico Agustín Codazzi (Ley 1447 de 2011, Decreto 1170 de
2015). Licencia CC BY 4.0 (confirmada en la metadata del item ArcGIS).
Confirmado en vivo el 2026-11-05: 1122 municipios (capa 0, `maxRecordCount`
2000).

https://services2.arcgis.com/RVvWzU3lgJISqdke/arcgis/rest/services/MunicipiosSNR/FeatureServer/0

**Migrado desde HDX el 2026-11-05** (ver git log de este archivo para el
extractor anterior): el recurso de HDX
(`data.humdata.org/dataset/cod-ab-col`) empezó a devolver un reto de AWS
WAF (`HTTP 202` + header `x-amzn-waf-action: challenge`, sin el zip real)
a cualquier cliente no-navegador — confirmado con `curl`/`requests` planos,
reproducible, no transitorio (3 builds en vivo consecutivos fallaron
igual). El extractor caía a su fallback embebido correctamente (`BadZipFile`
al parsear el reto como zip), pero eso colapsaba la geocodificación de
`infraestructura_poi` (que depende de este dataset) a solo 2 polígonos.
Este servicio ArcGIS no está detrás de ese WAF y es infraestructura global
de Esri, no un servidor gubernamental colombiano con historial de
caídas/bloqueos.

La API no permite traer los 1122 polígonos completos en una sola consulta
sin truncar la geometría (`exceededTransferLimit`) aunque esté bajo
`maxRecordCount`, así que se pagina por lotes de `objectIds`
(`_ARCGIS_BATCH_SIZE`) — confirmado en vivo que un lote de 150 no trunca.

Decisiones de alcance:

- **Geometría simplificada, no survey-grade.** El polígono original tiene
  ~5.7 millones de vértices en total (perfecto para GIS, pesado para una
  librería de propósito general). Se simplifica con tolerancia de 0.0005°
  (~55m en el ecuador, Douglas-Peucker con `preserve_topology=True`) y se
  redondean las coordenadas a 6 decimales (~11cm) antes de serializar a
  WKT — reduce el tamaño del dataset en >90% manteniendo la forma
  reconocible de cada municipio. No usar este dataset para análisis que
  requiera precisión catastral.
- **`area_km2` se calcula sobre la geometría ORIGINAL** (antes de
  simplificar), con área geodésica (`pyproj.Geod(ellps="WGS84")`), para que
  no cargue el error de la simplificación.
- **No se publica `nombre_mpio` aquí.** El nombre vive en `municipios`
  (mismo `cod_mpio`, join directo) — evita mantener dos copias del nombre
  que puedan divergir entre fuentes (DANE/DIVIPOLA vs. MGN/HDX).

Se invoca siempre como módulo, nunca como script suelto:
`python -m src.extractors.municipios_geometria_extractor` desde la raíz
del repo. Ver `.claude/rules/extractors.md` §6.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import polars as pl
import pyproj
import shapely
import shapely.wkt
from requests import RequestException
from shapely.errors import ShapelyError

from src.extractors.base import (
    RAW_DIR,
    ROOT_DIR,
    STAGING_DIR,
    BaseExtractor,
    ExtractionResult,
    ReusePolicy,
    compute_sha256,
    ensure_staging_directories,
    write_raw_snapshot_atomic,
    write_staging_csv_atomic,
)
from src.extractors.http_utils import get_json

DATASET_NAME = "municipios_geometria"
SOURCE_URL = (
    "https://services2.arcgis.com/RVvWzU3lgJISqdke/arcgis/rest/services/"
    "MunicipiosSNR/FeatureServer/0"
)
SOURCE_NAME = (
    "IGAC (Instituto Geográfico Agustín Codazzi), vía Superintendencia de "
    "Notariado y Registro (SNR) — servicio ArcGIS REST 'MunicipiosSNR'"
)
_ARCGIS_QUERY_URL = f"{SOURCE_URL}/query"
# Confirmado en vivo: un lote de 150 objectIds con geometría completa no
# trunca (`exceededTransferLimit`); 100 deja margen. Ver docstring del módulo.
_ARCGIS_BATCH_SIZE = 100

# ~55m en el ecuador — ver docstring del módulo.
SIMPLIFY_TOLERANCE_DEG = 0.0005
WKT_ROUNDING_PRECISION = 6

EXPECTED_MIN_ROWS = 1_100

REUSE_POLICY = ReusePolicy(
    status="open-attribution",
    license="CC BY 4.0",
    license_url="https://creativecommons.org/licenses/by/4.0/deed.es",
    attribution_required=True,
    redistribution_ok=True,
    summary=(
        "Límites municipales sobre cartografía del IGAC, publicados por la "
        "Superintendencia de Notariado y Registro bajo licencia abierta "
        "estándar CC BY 4.0 (confirmada en la metadata del item ArcGIS) — "
        "ver docs/licenses/data_licenses.md."
    ),
)

# Qué cae a fallback: problemas de la FUENTE (red caída, HTTP 4xx/5xx tras
# agotar reintentos, respuesta JSON con forma inesperada, geometría con forma
# inesperada). Un bug de programación real (AttributeError, NameError, etc.)
# debe reventar. Ver `.claude/rules/extractors.md` §1.
EXPECTED_FETCH_FAILURES: tuple[type[Exception], ...] = (
    RequestException,
    ShapelyError,
    KeyError,
    ValueError,
    TypeError,
)

# Fallback mínimo para desarrollo offline / CI sin red. NUNCA se publica.
# Geometría real observada en la fuente (2026-10-20), ya simplificada de
# forma agresiva (tolerancia 0.02-0.1°) para que el constante quede legible
# en el código — Medellín y Bogotá (Polygon) y San Andrés (MultiPolygon,
# para ejercitar ese tipo de geometría también offline).
MUNICIPIOS_GEOMETRIA_FALLBACK_DATA: list[dict[str, str]] = [
    {
        "ADM1_PCODE": "CO05",
        "ADM2_PCODE": "CO05001",
        "wkt": (
            "POLYGON ((-75.6697 6.3736, -75.6344 6.3173, -75.4992 6.2953, "
            "-75.4847 6.1909, -75.5324 6.1979, -75.5398 6.1703, -75.6131 6.1988, "
            "-75.68 6.1641, -75.7193 6.3415, -75.714 6.3714, -75.6697 6.3736))"
        ),
    },
    {
        "ADM1_PCODE": "CO11",
        "ADM2_PCODE": "CO11001",
        "wkt": (
            "POLYGON ((-74.0742 4.8365, -74.0056 4.8214, -74.0016 4.6753, "
            "-74.0314 4.6461, -73.9861 4.6291, -74.0053 4.5606, -74.0726 4.5131, "
            "-74.1121 4.4331, -74.0982 4.3456, -74.1527 4.2546, -74.11 4.1819, "
            "-74.1269 4.0485, -74.1507 4.0048, -74.2174 4.0109, -74.3168 3.8813, "
            "-74.2966 3.8189, -74.3356 3.8217, -74.4396 3.7306, -74.3596 3.9137, "
            "-74.3746 3.9859, -74.3299 4.1305, -74.2456 4.1032, -74.218 4.3608, "
            "-74.1736 4.5409, -74.2226 4.6294, -74.1585 4.6628, -74.177 4.7029, "
            "-74.1261 4.7294, -74.0742 4.8365))"
        ),
    },
    {
        "ADM1_PCODE": "CO88",
        "ADM2_PCODE": "CO88001",
        "wkt": (
            "MULTIPOLYGON (((-81.6897 12.5505, -81.6883 12.5506, -81.6885 12.5496, "
            "-81.6897 12.5505)), ((-81.6889 12.553, -81.6886 12.5524, "
            "-81.6892 12.5529, -81.6889 12.553)), ((-81.7323 12.5551, "
            "-81.6871 12.5809, -81.7301 12.4803, -81.7323 12.5551)), "
            "((-81.689 12.5996, -81.6907 12.5993, -81.6898 12.6011, -81.689 12.5996)))"
        ),
    },
]

_SCHEMA = {
    "cod_dpto": pl.Utf8,
    "cod_mpio": pl.Utf8,
    "geom_type": pl.Utf8,
    "area_km2": pl.Float64,
    "geometry_wkt": pl.Utf8,
}

_GEOD = pyproj.Geod(ellps="WGS84")


def _fallback_geodataframe() -> gpd.GeoDataFrame:
    rows = MUNICIPIOS_GEOMETRIA_FALLBACK_DATA
    return gpd.GeoDataFrame(
        {
            "ADM1_PCODE": [r["ADM1_PCODE"] for r in rows],
            "ADM2_PCODE": [r["ADM2_PCODE"] for r in rows],
        },
        geometry=[shapely.wkt.loads(r["wkt"]) for r in rows],
        crs="EPSG:4326",
    )


def _normalize(gdf: gpd.GeoDataFrame) -> tuple[pl.DataFrame, int, int]:
    """Devuelve (df, cod_mpio_duplicados, geometrias_invalidas). `gdf` trae
    como mínimo ADM1_PCODE, ADM2_PCODE y geometry en EPSG:4326."""
    if gdf.empty:
        return pl.DataFrame(schema=_SCHEMA), 0, 0

    invalid_mask = gdf.geometry.isna() | gdf.geometry.is_empty
    invalid_count = int(invalid_mask.sum())
    valid = gdf.loc[~invalid_mask].copy()

    valid["cod_dpto"] = valid["ADM1_PCODE"].astype(str).str[-2:].str.zfill(2)
    valid["cod_mpio"] = valid["ADM2_PCODE"].astype(str).str[-5:].str.zfill(5)

    records: list[dict[str, Any]] = []
    for row in valid.itertuples(index=False):
        geom = row.geometry
        area, _perimeter = _GEOD.geometry_area_perimeter(geom)
        simplified = geom.simplify(SIMPLIFY_TOLERANCE_DEG, preserve_topology=True)
        records.append(
            {
                "cod_dpto": row.cod_dpto,
                "cod_mpio": row.cod_mpio,
                "geom_type": simplified.geom_type,
                "area_km2": abs(area) / 1e6,
                "geometry_wkt": shapely.to_wkt(
                    simplified, rounding_precision=WKT_ROUNDING_PRECISION
                ),
            }
        )

    df = pl.DataFrame(records, schema=_SCHEMA)
    total = df.height
    df = df.unique(subset=["cod_mpio"], keep="first")
    duplicates = total - df.height
    return df.sort("cod_mpio"), duplicates, invalid_count


def _fetch_object_ids() -> list[int]:
    response = get_json(
        _ARCGIS_QUERY_URL,
        params={"where": "1=1", "returnIdsOnly": "true", "f": "json"},
        timeout=60,
    )
    object_ids: list[int] = response["objectIds"]
    if not object_ids:
        raise KeyError(f"el servicio ArcGIS no devolvió objectIds: {response!r}")
    return object_ids


def _fetch_features_batch(object_ids: list[int]) -> list[dict[str, Any]]:
    response = get_json(
        _ARCGIS_QUERY_URL,
        params={
            "objectIds": ",".join(str(oid) for oid in object_ids),
            "outFields": "MpCodigo",
            "outSR": "4326",
            "f": "geojson",
        },
        timeout=90,
    )
    features: list[dict[str, Any]] = response["features"]
    return features


def _fetch_geodataframe() -> tuple[gpd.GeoDataFrame, bytes]:
    """Trae los 1122 municipios del servicio ArcGIS en lotes de
    `_ARCGIS_BATCH_SIZE` objectIds (una sola consulta trunca la geometría,
    ver docstring del módulo), y arma el GeoDataFrame con las columnas
    ADM1_PCODE/ADM2_PCODE que espera `_normalize()` — mismo contrato que
    el extractor HDX anterior, derivadas de `MpCodigo` (ya viene como
    código DIVIPOLA de 5 dígitos, ej. "91001")."""
    object_ids = _fetch_object_ids()

    features: list[dict[str, Any]] = []
    for i in range(0, len(object_ids), _ARCGIS_BATCH_SIZE):
        batch = object_ids[i : i + _ARCGIS_BATCH_SIZE]
        features.extend(_fetch_features_batch(batch))

    for feature in features:
        cod_mpio = str(feature["properties"]["MpCodigo"]).zfill(5)
        feature["properties"]["ADM2_PCODE"] = f"CO{cod_mpio}"
        feature["properties"]["ADM1_PCODE"] = f"CO{cod_mpio[:2]}"

    raw_bytes = json.dumps({"type": "FeatureCollection", "features": features}).encode("utf-8")

    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    return gdf, raw_bytes


def _normalization_notes(duplicates: int, invalid: int) -> list[str]:
    notes: list[str] = []
    if duplicates > 0:
        notes.append(
            f"{duplicates} filas con cod_mpio duplicado — se conservó la primera "
            "aparición en la fuente."
        )
    if invalid > 0:
        notes.append(
            f"{invalid} filas con geometría ausente o vacía en la fuente — excluidas, "
            "no se fabrica un polígono de reemplazo."
        )
    return notes


class MunicipiosGeometriaExtractor(BaseExtractor):
    @property
    def dataset_name(self) -> str:
        return DATASET_NAME

    def fetch(self, **kwargs: Any) -> ExtractionResult:
        try:
            gdf, raw_bytes = _fetch_geodataframe()
            df, duplicates, invalid = _normalize(gdf)
            notes = _normalization_notes(duplicates, invalid)
            if df.height < EXPECTED_MIN_ROWS:
                notes.append(
                    f"La fuente devolvió solo {df.height} filas, menos de las "
                    f"{EXPECTED_MIN_ROWS} esperadas como mínimo."
                )

            ensure_staging_directories()
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            raw_path = RAW_DIR / f"municipios_geometria_{timestamp}.geojson"
            write_raw_snapshot_atomic(raw_path, raw_bytes)

            return ExtractionResult(
                dataset=DATASET_NAME,
                dataframe=df,
                source_name=SOURCE_NAME,
                source_url=SOURCE_URL,
                source_mode="live",
                source_detail=(
                    "Polígonos paginados del servicio ArcGIS 'MunicipiosSNR' (IGAC/SNR); "
                    f"geometría simplificada (tolerancia {SIMPLIFY_TOLERANCE_DEG}°) y "
                    f"redondeada a {WKT_ROUNDING_PRECISION} decimales — ver docstring "
                    "del extractor"
                ),
                reuse_policy=REUSE_POLICY,
                raw_snapshot_path=str(raw_path.relative_to(ROOT_DIR)),
                snapshot_hash=compute_sha256(raw_bytes),
                notes=notes,
            )
        except EXPECTED_FETCH_FAILURES as exc:
            df, duplicates, invalid = _normalize(_fallback_geodataframe())
            return ExtractionResult(
                dataset=DATASET_NAME,
                dataframe=df,
                source_name=SOURCE_NAME,
                source_url=SOURCE_URL,
                source_mode="fallback",
                source_detail=f"fallback embebido tras fallo de fetch en vivo: {exc!r}",
                reuse_policy=REUSE_POLICY,
                notes=[
                    "source_mode=fallback: dataset de muestra para desarrollo offline, "
                    "NO se publica.",
                    *_normalization_notes(duplicates, invalid),
                ],
            )

    def write_staging(self, result: ExtractionResult) -> Path:
        ensure_staging_directories()
        csv_path = STAGING_DIR / "municipios_geometria.csv"
        metadata_path = STAGING_DIR / "municipios_geometria.metadata.json"
        return write_staging_csv_atomic(
            result.dataframe, csv_path, metadata_path, result.to_staging_metadata()
        )


if __name__ == "__main__":
    extractor = MunicipiosGeometriaExtractor()
    outcome = extractor.run()
    print(f"[{DATASET_NAME}] source_mode={outcome.source_mode} rows={outcome.dataframe.height}")
