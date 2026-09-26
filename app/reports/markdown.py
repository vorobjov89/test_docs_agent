
from __future__ import annotations

from app.contracts.resolver import ContractCluster
from app.documents.models import Document


def render_cluster_report(
    cluster: ContractCluster,
    documents: dict[str, Document],
) -> str:
    docs = [documents[x] for x in cluster.document_ids]

    lines = [
        f"# История договора `{cluster.root_id}`",
        "",
        f"Количество документов: **{len(docs)}**",
        "",
        "## Хронология",
        "",
        "| Дата документа | Дата действия | Документ | Тип | Файл |",
        "|---|---|---|---|---|",
    ]

    for doc in docs:
        date_value = doc.document_date.isoformat() if doc.document_date else "не определена"
        effective_value = doc.effective_date.isoformat() if doc.effective_date else "—"
        lines.append(
            f"| {date_value} | {effective_value} | `{doc.document_id}` | "
            f"{doc.document_type.value} | `{doc.path.name}` |"
        )

    lines.extend(["", "## Связи", ""])

    for doc in docs:
        refs = [r for r in doc.referenced_contract_ids if r in documents]
        if refs:
            lines.append(f"- `{doc.document_id}` → {', '.join(f'`{r}`' for r in refs)}")

    warnings = [
        f"- `{d.document_id}`: {'; '.join(d.extraction_warnings)}"
        for d in docs if d.extraction_warnings
    ]
    if warnings:
        lines.extend(["", "## Предупреждения", ""])
        lines.extend(warnings)

    return "\n".join(lines) + "\n"
