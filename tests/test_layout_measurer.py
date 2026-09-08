"""core/layout/measurer.py — isolated render-to-scratch-page measurement.

Confirms the measurer never touches a real document (it opens/closes
its own throwaway `pymupdf.Document` per call) and gives sane,
deterministic answers.
"""

import pymupdf

from core.layout.measurer import TextMeasurer
from tests.fixtures.fit_cases import FONT_FILES, FONT_FAMILIES


def test_measure_fits_short_text_in_roomy_rect():
    measurer = TextMeasurer(font_dir="fonts/telugu")
    result = measurer.measure(
        "ఇది ఒక వాక్యం",
        pymupdf.Rect(0, 0, 400, 100),
        font_family=FONT_FAMILIES["te"],
        font_filename="NotoSans-telugu.ttf",
        font_size=14,
    )
    assert result.fits is True
    assert result.error is None
    assert result.spare_height >= 0


def test_measure_reports_no_fit_for_impossible_box():
    measurer = TextMeasurer(font_dir="fonts/telugu")
    result = measurer.measure(
        "This sentence is definitely too long for this box. " * 5,
        pymupdf.Rect(0, 0, 10, 5),
        font_family=FONT_FAMILIES["te"],
        font_filename="NotoSans-telugu.ttf",
        font_size=14,
    )
    assert result.fits is False
    assert result.spare_height == -1.0


def test_measure_is_deterministic():
    measurer = TextMeasurer(font_dir="fonts/telugu")
    kwargs = dict(
        text="ఇది ఒక పరీక్ష వాక్యం.",
        rect=pymupdf.Rect(0, 0, 150, 30),
        font_family=FONT_FAMILIES["te"],
        font_filename="NotoSans-telugu.ttf",
        font_size=14,
    )
    r1 = measurer.measure(**kwargs)
    r2 = measurer.measure(**kwargs)
    assert r1.fits == r2.fits
    assert r1.spare_height == r2.spare_height
    assert r1.scale == r2.scale


def test_measure_required_height_gives_a_usable_estimate():
    measurer = TextMeasurer(font_dir="fonts/telugu")
    height = measurer.measure_required_height(
        "ఇది ఒక పరీక్ష వాక్యం. ఇంకా కొంత టెక్స్ట్ ఇక్కడ ఉంది.",
        width=150,
        font_family=FONT_FAMILIES["te"],
        font_filename="NotoSans-telugu.ttf",
        font_size=14,
    )
    assert height > 0
    # A narrower width should generally require more height for the same text.
    height_wide = measurer.measure_required_height(
        "ఇది ఒక పరీక్ష వాక్యం. ఇంకా కొంత టెక్స్ట్ ఇక్కడ ఉంది.",
        width=500,
        font_family=FONT_FAMILIES["te"],
        font_filename="NotoSans-telugu.ttf",
        font_size=14,
    )
    assert height_wide <= height
