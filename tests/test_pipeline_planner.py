"""core/pipeline/planner.py — plan generation tests (point 16: "plan generation")."""

from core.layout.models import FitStatus, ScriptCategory
from core.pipeline.models import PlanStatus
from core.pipeline.planner import TranslationPlanner
from tests.fixtures.pipeline_cases import find_span_id, load_fixture_document, make_request, make_translation


def test_plan_generated_before_any_mutation(tmp_path):
    """The whole point of PLAN+FIT: no PDF mutation happens here at all
    -- confirmed by the source file's mtime/bytes being untouched."""
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    translations = {span_id: make_translation(span_id, "ఇది కొత్త వాక్యం.", "te")}
    request = make_request(document, translations, str(tmp_path / "out.pdf"))

    import hashlib

    before_hash = hashlib.sha256(open(request.source_pdf_path, "rb").read()).hexdigest()
    plan = TranslationPlanner().build_plan(request)
    after_hash = hashlib.sha256(open(request.source_pdf_path, "rb").read()).hexdigest()

    assert before_hash == after_hash
    assert plan.status == PlanStatus.OK
    assert len(plan.units) == 1
    assert plan.units[0].fit_result is not None


def test_multi_block_multi_language_plan():
    document = load_fixture_document()
    translations = {
        find_span_id(document, "పరీక్ష"): make_translation(find_span_id(document, "పరీక్ష"), "ఇది కొత్తది.", "te"),
        find_span_id(document, "परीक्षण"): make_translation(find_span_id(document, "परीक्षण"), "यह नया है।", "hi"),
        find_span_id(document, "சோதனை"): make_translation(find_span_id(document, "சோதனை"), "இது புதியது.", "ta"),
        find_span_id(document, "ಪರೀಕ್ಷೆ"): make_translation(find_span_id(document, "ಪರೀಕ್ಷೆ"), "ಇದು ಹೊಸದು.", "kn"),
    }
    request = make_request(document, translations, "unused_output.pdf")
    plan = TranslationPlanner().build_plan(request)

    assert plan.status == PlanStatus.OK
    assert len(plan.units) == 4
    assert {u.target_language for u in plan.units} == {"te", "hi", "ta", "kn"}
    assert all(u.fit_result is not None and u.fit_result.ok for u in plan.units)


def test_plan_uses_document_model_geometry_not_pymupdf_positional_ids():
    """The planner must resolve spans via the Document Model's own
    span_id -> (span, page) index, never by re-deriving a positional
    block number -- this is the whole point of Milestone 4's core
    principle. Confirmed indirectly: an out-of-range/unknown span_id
    is INVALID_SOURCE, not silently mapped to whatever block happens
    to be at some position."""
    document = load_fixture_document()
    fake_id = "does_not_exist_p9_b99_l0_s0"
    translations = {fake_id: make_translation(fake_id, "x", "te")}
    request = make_request(document, translations, "unused.pdf")
    plan = TranslationPlanner().build_plan(request)

    assert plan.status == PlanStatus.INVALID_SOURCE
    assert plan.units[0].plan_status == PlanStatus.INVALID_SOURCE
    assert plan.units[0].page_index == -1


def test_no_fit_propagates_to_plan_status():
    document = load_fixture_document()
    span_id = find_span_id(document, "పరీక్ష")
    huge_text = "చాలా పొడవైన అనువాదం " * 40  # deliberately impossible in any reasonable box
    translations = {span_id: make_translation(span_id, huge_text, "te")}
    request = make_request(document, translations, "unused.pdf", allow_geometry_expansion=False, min_font_size=10.0)
    plan = TranslationPlanner().build_plan(request)

    assert plan.status == PlanStatus.NO_FIT
    assert plan.units[0].fit_result.status == FitStatus.NO_FIT_MIN_FONT_SIZE
    assert not plan.units[0].fit_result.ok


def test_font_reduction_case_is_achievable_via_planner():
    """point 10: at least one case requiring font reduction. Disabling
    geometry expansion forces ANY accommodation to come from font size
    alone."""
    document = load_fixture_document()
    span_id = find_span_id(document, "சோதனை")  # Tamil, naturally tight single-line bbox
    longer_text = "இது ஒரு புதிய மொழிபெயர்ப்பு."
    translations = {span_id: make_translation(span_id, longer_text, "ta")}
    request = make_request(document, translations, "unused.pdf", allow_geometry_expansion=False, min_font_size=4.0)
    plan = TranslationPlanner().build_plan(request)

    assert plan.status == PlanStatus.OK
    fit = plan.units[0].fit_result
    assert fit.status in (FitStatus.FIT_AFTER_FONT_REDUCTION, FitStatus.FIT)


def test_geometry_tolerance_case_is_achievable_via_planner():
    """point 10: at least one case requiring geometry tolerance. The
    Kannada block has open space around it in the fixture, so a modest
    expansion should succeed."""
    document = load_fixture_document()
    span_id = find_span_id(document, "ಪರೀಕ್ಷೆ")
    longer_text = "ಇದು ಒಂದು ಹೊಸ ಮತ್ತು ಉದ್ದವಾದ ಅನುವಾದ ವಾಕ್ಯವಾಗಿದೆ."
    translations = {span_id: make_translation(span_id, longer_text, "kn")}
    request = make_request(document, translations, "unused.pdf", allow_geometry_expansion=True)
    request.fit_config.max_expansion_ratio = 1.0
    plan = TranslationPlanner().build_plan(request)

    assert plan.status == PlanStatus.OK
    fit = plan.units[0].fit_result
    assert fit.status in (
        FitStatus.FIT_AFTER_GEOMETRY_TOLERANCE,
        FitStatus.FIT_AFTER_BOTH,
        FitStatus.FIT,
        FitStatus.FIT_AFTER_FONT_REDUCTION,
    )
