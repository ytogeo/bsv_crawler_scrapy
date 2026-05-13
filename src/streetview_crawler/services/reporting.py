"""
运行报告服务，负责根据 MySQL 中的 job 状态生成结果报告。

该模块不参与采集流程本身，只在 job 结束后读取 MySQLRepository 提供的统计结果，
并写出机器可读和人工可读两类报告文件。

主要封装：
- write_report：生成 run_report.json 和 run_summary.md
- _rows_to_dict：将 SQL 聚合结果转换为报告字段
- _render_summary：渲染 Markdown 摘要
"""

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
        "pano_file": _rows_to_dict(counts["pano_file"], "status"),
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
        f"# 运行摘要：{report['job_id']}",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- pano 数量：{report['pano_count']}",
        f"- seed 状态：{report['seed']}",
        f"- pano 文件状态：{report['pano_file']}",
        f"- 错误统计：{report['errors']}",
        "",
        "## 错误样例",
        "",
    ]
    for item in report["error_samples"]:
        lines.append(f"- `{item['stage']}` `{item['error_type']}`: {item['error_message']}")
    lines.append("")
    return "\n".join(lines)
