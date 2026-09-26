
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.contracts.resolver import resolve_clusters
from app.documents.parser import parse_pdf
from app.reports.markdown import render_cluster_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports"))
    args = parser.parse_args()

    pdfs = sorted(args.input_dir.rglob("*.pdf"))
    documents = [parse_pdf(path) for path in pdfs]

    clusters = resolve_clusters(documents)
    by_id = {d.document_id: d for d in documents}

    args.output.mkdir(parents=True, exist_ok=True)

    for cluster in clusters:
        report = render_cluster_report(cluster, by_id)
        (args.output / f"{cluster.root_id}.md").write_text(report, encoding="utf-8")

    print(f"PDFs: {len(documents)}")
    print(f"Clusters: {len(clusters)}")
    for cluster in clusters:
        print(f"- {cluster.root_id}: {len(cluster.document_ids)} docs")


if __name__ == "__main__":
    main()
