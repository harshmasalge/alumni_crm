from app.core.field_permissions import FieldPermissionChecker


def make_checker():
    # FieldPermissionChecker only needs db for permission lookup; filtering is pure.
    return FieldPermissionChecker(db=None)  # type: ignore[arg-type]


def test_superuser_sees_everything():
    c = make_checker()
    data = {"final_cpi": 9.1, "roll_no": "X"}
    assert c.filter_dict("alumni_profile", data, set(), True) == data


def test_unrestricted_entity_passes_through():
    c = make_checker()
    data = {"education_stage": "IITGN", "qualification": "BTech"}
    assert c.filter_dict("education_record", data, set(), False) == data


def test_optional_restricted_field_dropped_without_permission():
    c = make_checker()
    data = {"roll_no": "R1", "final_cpi": 9.1, "year_of_graduation": 2020}
    out = c.filter_dict("alumni_profile", data, set(), False)
    assert out == {"roll_no": "R1", "year_of_graduation": 2020}


def test_optional_restricted_field_kept_with_permission():
    c = make_checker()
    data = {"roll_no": "R1", "final_cpi": 9.1}
    out = c.filter_dict("alumni_profile", data, {"alumni.read_academic"}, False)
    assert out == data


def test_required_restricted_field_masked_not_dropped():
    c = make_checker()
    data = {
        "contact_type": "EMAIL_IITGN",
        "value": "a@b.c",
        "normalised_value": "a@b.c",
        "is_primary": True,
    }
    out = c.filter_dict("contact_method", data, set(), False)
    assert out["value"] == "[restricted]"
    assert out["normalised_value"] == "[restricted]"
    assert out["contact_type"] == "EMAIL_IITGN"

    addr = {"address_type": "CURRENT", "line1": "42 Main St", "city": "X"}
    out_addr = c.filter_dict("address", addr, set(), False)
    assert out_addr["line1"] == "[restricted]"
    assert out_addr["city"] == "X"


def test_can_access_field():
    c = make_checker()
    assert c.can_access_field("person", "gender", {"people.read_demographics"}) is True
    assert c.can_access_field("person", "gender", set()) is False
    assert c.can_access_field("person", "gender", set(), True) is True
    assert c.can_access_field("education_record", "qualification", set()) is True


def test_filter_list_applies_to_each_item():
    c = make_checker()
    items = [
        {"roll_no": "R1", "final_cpi": 9.1},
        {"roll_no": "R2", "final_cpi": 8.0},
    ]
    out = c.filter_list("alumni_profile", items, set(), False)
    assert out == [{"roll_no": "R1"}, {"roll_no": "R2"}]
