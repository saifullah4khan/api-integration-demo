import pytest

from api_integration_demo.models import IntakeError, Lead, parse_intake


def test_maps_common_field_names():
    lead = parse_intake(
        {"full_name": "Ada Lovelace", "email_address": "ada@example.com", "msg": "hi"},
        source="form",
    )
    assert lead == Lead(
        name="Ada Lovelace",
        email="ada@example.com",
        message="hi",
        source="form",
        extra={},
    )


def test_unmapped_fields_preserved_in_extra():
    lead = parse_intake({"name": "Bo", "company": "Acme", "budget": "5k"})
    assert lead.extra == {"company": "Acme", "budget": "5k"}


def test_requires_name_or_email():
    with pytest.raises(IntakeError):
        parse_intake({"message": "just a note"})


def test_rejects_non_mapping():
    with pytest.raises(IntakeError):
        parse_intake("nope")  # type: ignore[arg-type]


def test_whitespace_only_values_ignored():
    lead = parse_intake({"name": "   ", "email": "x@y.com"})
    assert lead.name == ""
    assert lead.email == "x@y.com"


def test_summary_prefers_name_then_email():
    assert parse_intake({"name": "Ada", "email": "a@b.c"}).summary() == "New lead from Ada"
    assert parse_intake({"email": "a@b.c"}).summary() == "New lead from a@b.c"
