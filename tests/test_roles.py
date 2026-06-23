"""
Tests for the role-based access control mapping
(`backend.auth.roles`).

These tests pin down the canonical role design.
"""

from backend.auth.roles import (
    ALL_ROLES,
    get_allowed_collections,
    get_filters_for_role,
)
from backend.config import NURSE_ALLOWED_QTYPES


# Canonical design — must match the README role matrix.
EXPECTED_ACCESS = {
    "doctor": {"medical", "clinical", "nursing", "general"},
    "nurse": {"medical", "nursing", "general"},
    "billing_executive": {"billing", "general"},
    "technician": {"equipment", "general"},
    "admin": {"medical", "clinical", "billing", "equipment", "nursing", "general"},
}

# Defense-in-depth claim: these collections must NEVER appear for these roles.
FORBIDDEN_ACCESS = {
    "nurse": {"billing", "equipment", "clinical"},
    "billing_executive": {"medical", "clinical", "nursing", "equipment"},
    "technician": {"medical", "clinical", "nursing", "billing"},
}


class TestRoleCollections:
    def test_known_roles_complete(self):
        assert set(ALL_ROLES) == set(EXPECTED_ACCESS)

    def test_each_role_has_expected_collections(self):
        for role, expected in EXPECTED_ACCESS.items():
            assert set(get_allowed_collections(role)) == expected, (
                f"Role '{role}' access mismatch — collections matrix changed?"
            )

    def test_forbidden_collections_never_accessible(self):
        # This is the security test. If RBAC ever regresses, this fails loud.
        for role, forbidden in FORBIDDEN_ACCESS.items():
            allowed = set(get_allowed_collections(role))
            leaked = forbidden & allowed
            assert not leaked, f"Role '{role}' must not access {leaked}"

    def test_unknown_role_returns_empty(self):
        # Closed-by-default: unknown roles see nothing.
        assert get_allowed_collections("hacker") == []
        assert get_allowed_collections("") == []

    def test_admin_sees_all_collections(self):
        admin_collections = set(get_allowed_collections("admin"))
        # Union of every other role's allowed collections must be a subset of admin's.
        union_of_others = set().union(
            *(set(get_allowed_collections(r)) for r in ALL_ROLES if r != "admin")
        )
        assert union_of_others.issubset(admin_collections)


class TestNurseQTypeFilter:
    def test_nurse_on_medical_has_qtype_filter(self):
        where_filter, allowed_qtypes = get_filters_for_role("nurse", "medical")
        assert where_filter == {"qtype": {"$in": NURSE_ALLOWED_QTYPES}}
        assert allowed_qtypes == NURSE_ALLOWED_QTYPES

    def test_nurse_on_nursing_has_no_qtype_filter(self):
        # Nurse's own collection — no additional filter.
        where_filter, allowed_qtypes = get_filters_for_role("nurse", "nursing")
        assert where_filter is None
        assert allowed_qtypes is None

    def test_doctor_on_medical_has_no_qtype_filter(self):
        # Doctors get unrestricted access to medical Q&A.
        where_filter, allowed_qtypes = get_filters_for_role("doctor", "medical")
        assert where_filter is None
        assert allowed_qtypes is None
