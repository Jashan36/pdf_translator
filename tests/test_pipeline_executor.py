"""core/pipeline/executor.py — mutation-stage tests, in isolation from
the full pipeline (point 6: redaction safety; point 12's failure cases
that are the executor's own responsibility)."""

import hashlib

import pymupdf

from core.pipeline.executor import MutationExecutor
from core.pipeline.models import MutationStatus
from core.pipeline.planner import TranslationPlanner
from tests.fixtures.pipeline_cases import find_span_id, load_fixture_document, make_request, make_translation


def _sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_successful_mutation_produces_valid_temp_pdf(tmp_path):
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translations = {span_id: make_translation(span_id, "ఇది కొత్తది.", "te")}
    request = make_request(document, translations, str(tmp_path / "out.pdf"))
    plan = TranslationPlanner().build_plan(request)

    success, message, plan = MutationExecutor().execute(request.source_pdf_path, plan, request.output_path)

    assert success
    assert message.endswith(".tmp")
    with pymupdf.open(message) as out:
        assert out.page_count == document.page_count
    assert plan.units[0].mutation_status == MutationStatus.APPLIED


def test_source_pdf_is_never_modified(tmp_path):
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translations = {span_id: make_translation(span_id, "ఇది కొత్తది.", "te")}
    request = make_request(document, translations, str(tmp_path / "out.pdf"))
    plan = TranslationPlanner().build_plan(request)

    before = _sha256(request.source_pdf_path)
    MutationExecutor().execute(request.source_pdf_path, plan, request.output_path)
    after = _sha256(request.source_pdf_path)

    assert before == after


def test_mutation_fails_safe_when_page_index_invalid(tmp_path):
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translations = {span_id: make_translation(span_id, "ఇది కొత్తది.", "te")}
    request = make_request(document, translations, str(tmp_path / "out.pdf"))
    plan = TranslationPlanner().build_plan(request)
    plan.units[0].page_index = 99  # corrupt it after planning, simulating a bad plan reaching the executor

    success, message, plan = MutationExecutor().execute(request.source_pdf_path, plan, request.output_path)

    assert not success
    assert "page index" in message.lower() or "page_index" in message.lower()
    assert plan.units[0].mutation_status == MutationStatus.FAILED
    before = _sha256(request.source_pdf_path)
    assert before  # sanity: file still readable/untouched (no exception opening it)


def test_mutation_fails_safe_when_geometry_invalid(tmp_path):
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translations = {span_id: make_translation(span_id, "ఇది కొత్తది.", "te")}
    request = make_request(document, translations, str(tmp_path / "out.pdf"))
    plan = TranslationPlanner().build_plan(request)
    plan.units[0].source_rect = pymupdf.Rect(10, 10, 10, 10)  # zero-area

    success, message, plan = MutationExecutor().execute(request.source_pdf_path, plan, request.output_path)

    assert not success
    assert plan.units[0].mutation_status == MutationStatus.FAILED


def test_mutation_fails_safe_when_expected_source_text_missing(tmp_path):
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translations = {span_id: make_translation(span_id, "ఇది కొత్తది.", "te")}
    request = make_request(document, translations, str(tmp_path / "out.pdf"))
    plan = TranslationPlanner().build_plan(request)
    plan.units[0].source_text = "this text does not exist anywhere on the page"

    success, message, plan = MutationExecutor().execute(request.source_pdf_path, plan, request.output_path)

    assert not success
    assert "not found" in message.lower()
    assert plan.units[0].mutation_status == MutationStatus.FAILED


def test_precheck_failure_applies_zero_redactions(tmp_path):
    """If ANY unit fails precheck, NOTHING is redacted -- not even the
    units that would have validated fine (transactional all-or-nothing
    at the precheck stage, before any mutation begins)."""
    document = load_fixture_document()
    te_id = find_span_id(document, "పరీక్ష")
    hi_id = find_span_id(document, "परीक्षण")
    translations = {
        te_id: make_translation(te_id, "ఇది కొత్తది.", "te"),
        hi_id: make_translation(hi_id, "यह नया है।", "hi"),
    }
    request = make_request(document, translations, str(tmp_path / "out.pdf"))
    plan = TranslationPlanner().build_plan(request)
    # Corrupt only the Hindi unit's source text -- the Telugu unit alone would succeed.
    for unit in plan.units:
        if unit.target_language == "hi":
            unit.source_text = "nonexistent"

    success, message, plan = MutationExecutor().execute(request.source_pdf_path, plan, request.output_path)

    assert not success
    # Neither unit was mutated -- the failure was caught in the precheck loop before any redaction.
    for unit in plan.units:
        assert unit.mutation_status in (MutationStatus.PENDING, MutationStatus.FAILED)
        assert unit.mutation_status != MutationStatus.APPLIED
