from app.routers.copilot import _source_provenance


def test_provenance_has_authoritative_backend_sources():
    result = _source_provenance(1, course_codes=["CS402", "math201"])
    ids = {item["id"] for item in result["sources"]}
    assert {"KG-COURSE-CATALOG", "KG-PREREQUISITES", "MYSQL-STUDENT-RECORD"} <= ids
    assert result["student_scope"] == "student:1"
    assert result["course_codes"] == ["CS402", "MATH201"]


def test_llm_provenance_is_explicitly_non_authoritative():
    result = _source_provenance(1, ai_used=True)
    llm = next(item for item in result["sources"] if item["id"] == "LLM-SYNTHESIS")
    assert llm["authority"] == "non-authoritative"
    assert "Natural-language synthesis only" in llm["scope"]
