"""Tests for the public clean_name and its equivalence with the pipeline version.

The two implementations are intentionally duplicated (public library cannot import
from builders/). These tests ensure they stay in sync.
"""

import pytest

from src.builders.datasets import clean_name as pipeline_clean_name
from src.colombia_open.text import clean_name


@pytest.mark.parametrize(
    "input_name, expected",
    [
        ("Nariño", "narino"),
        ("BOGOTÁ, D.C.", "bogota_d_c"),
        ("San José de Cúcuta", "san_jose_de_cucuta"),
        ("Archipiélago de San Andrés, Providencia y Santa Catalina", "archipielago_de_san_andres_providencia_y_santa_catalina"),
        ("El Carmen de Viboral", "el_carmen_de_viboral"),
        ("Güepsa", "guepsa"),
        ("Abejorral", "abejorral"),
        ("", ""),
        ("   ", ""),
        ("!!!", ""),
        ("a--b  c", "a_b_c"),
        ("Méd-ellín", "med_ellin"),
    ],
)
def test_clean_name_cases(input_name: str, expected: str) -> None:
    assert clean_name(input_name) == expected


DIFFICULT_NAMES = [
    "San José de Cúcuta",
    "Archipiélago de San Andrés, Providencia y Santa Catalina",
    "El Carmen de Viboral",
    "Güepsa",
    "Bogotá, D.C.",
    "Nariño",
    "MEDELLÍN",
    "BOGOTÁ, D.C.",
    "a--b  c",
    "",
    "!!!",
]


@pytest.mark.parametrize("name", DIFFICULT_NAMES)
def test_clean_name_equivalence(name: str) -> None:
    """Both clean_name implementations must produce identical results."""
    assert clean_name(name) == pipeline_clean_name(name)
