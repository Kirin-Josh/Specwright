from app.pipeline.agents import spec_id_prefixes
from app.schemas import SpecDocument, SpecSection


def doc(markdown: str) -> SpecDocument:
    return SpecDocument(title="t", sections=[SpecSection(heading="h", markdown=markdown)])


def test_prefixes_from_lists_and_table_rows():
    markdown = (
        "| ID | Exigence |\n|---|---|\n| EF-01 | Créer |\n| EF-02 | Joindre |\n"
        "- **ES-01** — CAS\n- **ES-02** — Accès\n"
        "Voir UT-CDC-SAAS-001 et UT-CDC-SAAS-002 dans le texte.\n"
    )
    assert spec_id_prefixes(doc(markdown)) == ["EF", "ES"]
