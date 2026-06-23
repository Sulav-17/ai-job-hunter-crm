from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SkillCatalogEntry:
    name: str
    normalized_name: str
    aliases: tuple[str, ...]


SKILL_CATALOG: tuple[SkillCatalogEntry, ...] = (
    SkillCatalogEntry("Python", "python", ("python",)),
    SkillCatalogEntry("SQL", "sql", ("sql",)),
    SkillCatalogEntry("PostgreSQL", "postgresql", ("postgresql", "postgres")),
    SkillCatalogEntry("MySQL", "mysql", ("mysql",)),
    SkillCatalogEntry(
        "Microsoft SQL Server",
        "microsoft_sql_server",
        ("microsoft sql server", "sql server", "ms sql server"),
    ),
    SkillCatalogEntry("Excel", "excel", ("excel", "ms excel", "microsoft excel")),
    SkillCatalogEntry("Power BI", "power_bi", ("power bi", "powerbi")),
    SkillCatalogEntry("Tableau", "tableau", ("tableau",)),
    SkillCatalogEntry("Pandas", "pandas", ("pandas",)),
    SkillCatalogEntry("NumPy", "numpy", ("numpy", "num py")),
    SkillCatalogEntry(
        "Scikit-learn",
        "scikit_learn",
        ("scikit-learn", "scikit learn", "sklearn"),
    ),
    SkillCatalogEntry("FastAPI", "fastapi", ("fastapi", "fast api")),
    SkillCatalogEntry("Django", "django", ("django",)),
    SkillCatalogEntry("Flask", "flask", ("flask",)),
    SkillCatalogEntry("REST APIs", "rest_apis", ("rest apis", "rest api", "restful api")),
    SkillCatalogEntry("Git", "git", ("git",)),
    SkillCatalogEntry("GitHub", "github", ("github", "git hub")),
    SkillCatalogEntry("Docker", "docker", ("docker",)),
    SkillCatalogEntry("Kubernetes", "kubernetes", ("kubernetes", "k8s")),
    SkillCatalogEntry("AWS", "aws", ("aws", "amazon web services")),
    SkillCatalogEntry("Azure", "azure", ("azure", "microsoft azure")),
    SkillCatalogEntry(
        "Google Cloud",
        "google_cloud",
        ("google cloud", "google cloud platform", "gcp"),
    ),
    SkillCatalogEntry("Spark", "spark", ("spark", "apache spark")),
    SkillCatalogEntry("PySpark", "pyspark", ("pyspark", "py spark")),
    SkillCatalogEntry("Airflow", "airflow", ("airflow", "apache airflow")),
    SkillCatalogEntry("dbt", "dbt", ("dbt",)),
    SkillCatalogEntry("Redis", "redis", ("redis",)),
    SkillCatalogEntry("MongoDB", "mongodb", ("mongodb", "mongo db")),
    SkillCatalogEntry("Java", "java", ("java",)),
    SkillCatalogEntry("JavaScript", "javascript", ("javascript", "java script")),
    SkillCatalogEntry("TypeScript", "typescript", ("typescript", "type script")),
    SkillCatalogEntry("React", "react", ("react", "react.js", "reactjs")),
    SkillCatalogEntry(
        "Machine Learning",
        "machine_learning",
        ("machine learning",),
    ),
    SkillCatalogEntry("Data Analysis", "data_analysis", ("data analysis",)),
    SkillCatalogEntry("Data Engineering", "data_engineering", ("data engineering",)),
    SkillCatalogEntry("ETL", "etl", ("etl",)),
    SkillCatalogEntry("Agile", "agile", ("agile",)),
    SkillCatalogEntry("Scrum", "scrum", ("scrum",)),
    SkillCatalogEntry("Node.js", "node_js", ("node.js", "nodejs", "node js")),
    SkillCatalogEntry("R", "r", ("r",)),
    SkillCatalogEntry("C", "c", ("c",)),
)


def normalize_alias_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def get_catalog_entries() -> tuple[SkillCatalogEntry, ...]:
    return SKILL_CATALOG


def get_alias_lookup() -> dict[str, SkillCatalogEntry]:
    lookup: dict[str, SkillCatalogEntry] = {}
    for entry in SKILL_CATALOG:
        lookup[normalize_alias_text(entry.name)] = entry
        lookup[entry.normalized_name] = entry
        for alias in entry.aliases:
            lookup[normalize_alias_text(alias)] = entry
    return lookup


def find_catalog_entry(value: str) -> SkillCatalogEntry | None:
    return get_alias_lookup().get(normalize_alias_text(value))
