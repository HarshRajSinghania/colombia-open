import geopandas as gpd
import polars as pl
import pytest
import shapely
import shapely.affinity
import shapely.wkt
from shapely.geometry import MultiPolygon, Polygon

import src.extractors.base as base_module
import src.extractors.municipios_geometria_extractor as geometria_module
from src.extractors.municipios_geometria_extractor import (
    MUNICIPIOS_GEOMETRIA_FALLBACK_DATA,
    MunicipiosGeometriaExtractor,
    _fallback_geodataframe,
    _fetch_geodataframe,
    _fetch_object_ids,
    _normalize,
)

# Un cuadrado simple de ~0.01° de lado (~1km), suficiente para ejercitar
# simplify/área/WKT sin depender de geometría real descargada.
_SQUARE = Polygon([(0.0, 0.0), (0.0, 0.01), (0.01, 0.01), (0.01, 0.0), (0.0, 0.0)])


def _gdf(rows: list[dict[str, object]]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "ADM1_PCODE": [r["ADM1_PCODE"] for r in rows],
            "ADM2_PCODE": [r["ADM2_PCODE"] for r in rows],
        },
        geometry=[r["geometry"] for r in rows],
        crs="EPSG:4326",
    )


def test_normalize_fallback_rows_have_fixed_width_codes():
    df, duplicates, invalid = _normalize(_fallback_geodataframe())
    assert duplicates == 0
    assert invalid == 0
    assert df.height == len(MUNICIPIOS_GEOMETRIA_FALLBACK_DATA)
    assert all(len(c) == 2 for c in df["cod_dpto"].to_list())
    assert all(len(c) == 5 for c in df["cod_mpio"].to_list())


def test_normalize_derives_codes_from_pcode():
    df, _dup, _inv = _normalize(
        _gdf([{"ADM1_PCODE": "CO05", "ADM2_PCODE": "CO05001", "geometry": _SQUARE}])
    )
    assert df["cod_dpto"].to_list() == ["05"]
    assert df["cod_mpio"].to_list() == ["05001"]


def test_normalize_computes_positive_area_km2():
    df, _dup, _inv = _normalize(
        _gdf([{"ADM1_PCODE": "CO05", "ADM2_PCODE": "CO05001", "geometry": _SQUARE}])
    )
    area = df["area_km2"].item()
    assert area > 0
    # Un cuadrado de ~0.01° de lado en el ecuador mide ~1.1km de lado.
    assert 0.5 < area < 3


def test_normalize_serializes_polygon_to_wkt_and_classifies_geom_type():
    df, _dup, _inv = _normalize(
        _gdf([{"ADM1_PCODE": "CO05", "ADM2_PCODE": "CO05001", "geometry": _SQUARE}])
    )
    row = df.row(0, named=True)
    assert row["geom_type"] == "Polygon"
    assert row["geometry_wkt"].startswith("POLYGON")
    # Reconstruible: el WKT publicado debe parsear de vuelta a un polígono válido.
    assert shapely.wkt.loads(row["geometry_wkt"]).is_valid


def test_normalize_classifies_multipolygon():
    multi = MultiPolygon([_SQUARE, shapely.affinity.translate(_SQUARE, xoff=1.0)])
    df, _dup, _inv = _normalize(
        _gdf([{"ADM1_PCODE": "CO88", "ADM2_PCODE": "CO88001", "geometry": multi}])
    )
    row = df.row(0, named=True)
    assert row["geom_type"] == "MultiPolygon"
    assert row["geometry_wkt"].startswith("MULTIPOLYGON")


def test_normalize_excludes_rows_with_missing_or_empty_geometry():
    rows = [
        {"ADM1_PCODE": "CO05", "ADM2_PCODE": "CO05001", "geometry": _SQUARE},
        {"ADM1_PCODE": "CO05", "ADM2_PCODE": "CO05002", "geometry": None},
        {"ADM1_PCODE": "CO05", "ADM2_PCODE": "CO05004", "geometry": Polygon()},
    ]
    df, _dup, invalid = _normalize(_gdf(rows))
    assert invalid == 2
    assert df.height == 1
    assert df["cod_mpio"].to_list() == ["05001"]


def test_normalize_deduplicates_cod_mpio_keeping_first():
    rows = [
        {"ADM1_PCODE": "CO05", "ADM2_PCODE": "CO05001", "geometry": _SQUARE},
        {"ADM1_PCODE": "CO05", "ADM2_PCODE": "CO05001", "geometry": _SQUARE},
    ]
    df, duplicates, _invalid = _normalize(_gdf(rows))
    assert duplicates == 1
    assert df.height == 1


def test_normalize_empty_input_returns_empty_frame_with_schema():
    df, duplicates, invalid = _normalize(_gdf([]))
    assert df.height == 0
    assert (duplicates, invalid) == (0, 0)
    assert df.schema["cod_mpio"] == pl.Utf8


def _geojson_feature(mp_codigo: str) -> dict[str, object]:
    return {
        "type": "Feature",
        "properties": {"MpCodigo": mp_codigo},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0.0, 0.0], [0.0, 0.01], [0.01, 0.01], [0.01, 0.0], [0.0, 0.0]]],
        },
    }


def test_fetch_object_ids_returns_ids_from_arcgis_response(monkeypatch):
    monkeypatch.setattr(
        geometria_module,
        "get_json",
        lambda *_a, **_k: {"objectIds": [1, 2, 3]},
    )
    assert _fetch_object_ids() == [1, 2, 3]


def test_fetch_object_ids_raises_keyerror_on_empty_response(monkeypatch):
    monkeypatch.setattr(geometria_module, "get_json", lambda *_a, **_k: {"objectIds": []})
    with pytest.raises(KeyError):
        _fetch_object_ids()


def test_fetch_geodataframe_paginates_and_derives_pcodes_from_mpcodigo(monkeypatch):
    # 3 objectIds, tamaño de lote forzado a 2 -> 2 llamadas a /query con
    # geometría (además de la llamada a returnIdsOnly).
    monkeypatch.setattr(geometria_module, "_ARCGIS_BATCH_SIZE", 2)
    batch_sizes: list[int] = []

    def _fake_get_json(_url, *, params, timeout=None):
        del timeout
        if params.get("returnIdsOnly") == "true":
            return {"objectIds": [1, 2, 3]}
        ids = params["objectIds"].split(",")
        batch_sizes.append(len(ids))
        codes = {"1": "05001", "2": "11001", "3": "91001"}
        return {
            "type": "FeatureCollection",
            "features": [_geojson_feature(codes[i]) for i in ids],
        }

    monkeypatch.setattr(geometria_module, "get_json", _fake_get_json)

    gdf, raw_bytes = _fetch_geodataframe()

    assert batch_sizes == [2, 1]
    assert len(raw_bytes) > 0
    assert sorted(gdf["ADM2_PCODE"].tolist()) == ["CO05001", "CO11001", "CO91001"]
    assert sorted(gdf["ADM1_PCODE"].tolist()) == ["CO05", "CO11", "CO91"]


def test_extractor_dry_run_never_writes(tmp_path, monkeypatch):
    # Ver test_divipola_extractor.py: hay que parchear los paths tanto en
    # base.py como en el módulo del extractor.
    monkeypatch.setattr(base_module, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(base_module, "STAGING_DIR", tmp_path / "staging")
    monkeypatch.setattr(geometria_module, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(geometria_module, "STAGING_DIR", tmp_path / "staging")
    monkeypatch.setattr(geometria_module, "ROOT_DIR", tmp_path)

    monkeypatch.setattr(
        geometria_module,
        "_fetch_geodataframe",
        lambda: (_fallback_geodataframe(), b"zip-bytes-de-prueba"),
    )

    result = MunicipiosGeometriaExtractor().run(dry_run=True)

    assert result.dataset == "municipios_geometria"
    assert result.source_mode == "live"
    assert result.dataframe.height == len(MUNICIPIOS_GEOMETRIA_FALLBACK_DATA)
    assert not (tmp_path / "staging" / "municipios_geometria.csv").exists()
    assert not (tmp_path / "staging" / "municipios_geometria.metadata.json").exists()


def test_fetch_falls_back_on_expected_source_failure(monkeypatch):
    def _bad_fetch() -> None:
        raise KeyError("shapefile ADM2 no encontrado en el zip")

    monkeypatch.setattr(geometria_module, "_fetch_geodataframe", _bad_fetch)

    result = MunicipiosGeometriaExtractor().fetch()
    assert result.source_mode == "fallback"
    assert result.dataframe.height > 0


def test_fetch_propagates_unexpected_bugs_instead_of_hiding_as_fallback(monkeypatch):
    def _broken_fetch() -> None:
        raise AttributeError("bug de programación simulado, no una falla de red")

    monkeypatch.setattr(geometria_module, "_fetch_geodataframe", _broken_fetch)

    with pytest.raises(AttributeError):
        MunicipiosGeometriaExtractor().fetch()
