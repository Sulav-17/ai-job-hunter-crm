from backend.services.skill_catalog import find_catalog_entry, get_alias_lookup


def test_aliases_resolve_to_same_canonical_skill() -> None:
    postgres = find_catalog_entry("postgres")
    postgresql = find_catalog_entry("PostgreSQL")

    assert postgres is not None
    assert postgresql is not None
    assert postgres.name == "PostgreSQL"
    assert postgresql.name == "PostgreSQL"
    assert postgres.normalized_name == "postgresql"
    assert postgresql.normalized_name == "postgresql"


def test_alias_lookup_is_case_insensitive() -> None:
    entry = find_catalog_entry(" POWERBI ")

    assert entry is not None
    assert entry.name == "Power BI"
    assert entry.normalized_name == "power_bi"


def test_multiple_aliases_map_to_one_canonical_skill() -> None:
    aliases = get_alias_lookup()

    assert aliases["scikit learn"].normalized_name == "scikit_learn"
    assert aliases["sklearn"].normalized_name == "scikit_learn"
    assert aliases["rest api"].normalized_name == "rest_apis"
    assert aliases["restful api"].normalized_name == "rest_apis"
    assert aliases["amazon web services"].normalized_name == "aws"
    assert aliases["google cloud platform"].normalized_name == "google_cloud"
