"""
Role-based access control definitions.

Maps each role to its allowed collections and any metadata
filters (e.g. nurse qtype restrictions on medical collection).
"""

from backend.config import NURSE_ALLOWED_QTYPES

ROLE_COLLECTIONS: dict[str, list[str]] = {
    "doctor": ["medical", "clinical", "nursing", "general"],
    "nurse": ["medical", "nursing", "general"],
    "billing_executive": ["billing", "general"],
    "technician": ["equipment", "general"],
    "admin": ["medical", "clinical", "billing", "equipment", "nursing", "general"],
}

ALL_ROLES = list(ROLE_COLLECTIONS.keys())


def get_allowed_collections(role: str) -> list[str]:
    """Return list of collection names this role can access."""
    return ROLE_COLLECTIONS.get(role, [])


def get_filters_for_role(
    role: str, collection_name: str
) -> tuple[dict | None, list[str] | None]:
    """
    Determine metadata filters based on role and collection.

    Returns:
        (where_filter, allowed_qtypes) — both None if no filtering needed.
    """
    if role == "nurse" and collection_name == "medical":
        return (
            {"qtype": {"$in": NURSE_ALLOWED_QTYPES}},
            NURSE_ALLOWED_QTYPES,
        )
    return None, None
