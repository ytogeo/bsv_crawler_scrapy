from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from streetview_crawler.config import resolve_path
from streetview_crawler.services.db import MySQLRepository


def write_report(job_id: str, config: dict[str, Any], db: MySQLRepository) -> dict[str, Any]:
    report_dir = resolve_path(config, config.get("report_dir", "data/reports")) / job_id
    report_dir.mkdir(parents=True, exist_ok=True)
    counts = db.job_counts(job_id)
    report = {
        "job_id": job_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "config_path": config.get("_config_path"),
        "seed": _rows_to_dict(counts["seed"], "status"),
        "pano_count": counts["pano_count"],
        "asset": _rows_to_dict(counts["asset"], "status"),
        "errors": _rows_to_dict(counts["errors"], "stage"),
        "error_samples": counts["error_samples"],
    }

    (report_dir / "run_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (report_dir / "run_summary.md").write_text(_render_summary(report), encoding="utf-8")
    return report


def _rows_to_dict(rows: list[dict[str, Any]], key_name: str) -> dict[str, int]:
    return {str(row[key_name]): int(row["count"]) for row in rows}


def _render_summary(report: dict[str, Any]) -> str:
    lines = [
        f"# Run Summary: {report['job_id']}",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Pano count: {report['pano_count']}",
        f"- Seed status: {report['seed']}",
        f"- Asset status: {report['asset']}",
        f"- Errors: {report['errors']}",
        "",
        "## Error Samples",
        "",
    ]
    for item in report["error_samples"]:
        lines.append(f"- `{item['stage']}` `{item['error_type']}`: {item['error_message']}")
    lines.append("")
    return "\n".join(lines)

