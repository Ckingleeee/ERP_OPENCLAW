"""Command-line entry point for the first-stage evaluation baseline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from statistics import mean

from evals.eval_core import grade_result, load_jsonl, scaffold_result, validate_cases


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "evals" / "cases" / "golden_v1.jsonl"


def _case_map(path: Path) -> dict[str, dict]:
    cases = load_jsonl(path)
    errors = validate_cases(cases)
    if errors:
        raise ValueError("\n".join(errors))
    return {case["id"]: case for case in cases}


def command_validate(args: argparse.Namespace) -> int:
    cases = load_jsonl(args.cases)
    errors = validate_cases(cases)
    if errors:
        print("评测用例校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1
    categories = sorted({case["category"] for case in cases})
    print(f"评测用例校验通过：{len(cases)} 条")
    print("类别：" + ", ".join(categories))
    return 0


def command_scaffold(args: argparse.Namespace) -> int:
    cases = _case_map(args.cases)
    if args.output.exists() and not args.force:
        raise ValueError(
            f"结果文件已存在：{args.output}；如需覆盖请显式传入 --force"
        )
    records = [
        scaffold_result(case, run_number)
        for run_number in range(1, args.runs + 1)
        for case in cases.values()
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    print(f"已生成待填写结果：{args.output}（{len(records)} 条）")
    return 0


def _render_markdown(grades: list[dict], metadata: dict) -> str:
    graded = [item for item in grades if item["status"] == "graded"]
    scores = [item["score"] for item in graded]
    passed = sum(1 for item in graded if item["passed"])
    hard_failed = sum(1 for item in graded if item["hard_failures"])
    average = round(mean(scores), 2) if scores else None

    lines = [
        "# Agent 评测报告",
        "",
        f"- 生成时间：{metadata['generated_at']}",
        f"- 用例文件：`{metadata['cases']}`",
        f"- 结果文件：`{metadata['results']}`",
        f"- 已评分：{len(graded)}/{len(grades)}",
        f"- 通过：{passed}",
        f"- 硬性失败：{hard_failed}",
        f"- 平均分：{average if average is not None else '尚无'}",
        "",
        "## 用例结果",
        "",
        "| 用例 | 状态 | 得分 | 通过 | 硬性失败 | 主要问题 |",
        "|---|---|---:|---|---|---|",
    ]
    for item in grades:
        details = "；".join(item["details"][:3]) or "-"
        hard = "；".join(item["hard_failures"]) or "-"
        score = "-" if item["score"] is None else str(item["score"])
        lines.append(
            f"| {item['case_id']} | {item['status']} | {score} | "
            f"{'是' if item['passed'] else '否'} | {hard} | {details} |"
        )
    lines.append("")
    return "\n".join(lines)


def command_score(args: argparse.Namespace) -> int:
    cases = _case_map(args.cases)
    results = load_jsonl(args.results)
    grades: list[dict] = []
    unknown_case_ids: list[str] = []

    for result in results:
        case_id = result.get("case_id")
        case = cases.get(case_id)
        if case is None:
            unknown_case_ids.append(str(case_id))
            continue
        grades.append(grade_result(case, result).as_dict())

    if unknown_case_ids:
        raise ValueError("结果包含未知用例：" + ", ".join(unknown_case_ids))

    metadata = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "cases": str(args.cases),
        "results": str(args.results),
    }
    payload = {"metadata": metadata, "grades": grades}
    args.json_report.parent.mkdir(parents=True, exist_ok=True)
    args.json_report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_report.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_report.write_text(
        _render_markdown(grades, metadata), encoding="utf-8"
    )

    graded_count = sum(item["status"] == "graded" for item in grades)
    print(f"报告已生成：{args.markdown_report}")
    print(f"已评分：{graded_count}/{len(grades)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="卡营智控 Agent 评测工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="校验评测用例")
    validate.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    validate.set_defaults(func=command_validate)

    scaffold = subparsers.add_parser("scaffold", help="生成待填写结果文件")
    scaffold.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    scaffold.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evals" / "results" / "manual_v1.jsonl",
    )
    scaffold.add_argument("--runs", type=int, default=1, choices=range(1, 6))
    scaffold.add_argument(
        "--force", action="store_true", help="显式覆盖已经存在的结果文件"
    )
    scaffold.set_defaults(func=command_scaffold)

    score = subparsers.add_parser("score", help="评分并生成报告")
    score.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    score.add_argument(
        "--results",
        type=Path,
        default=ROOT / "evals" / "results" / "manual_v1.jsonl",
    )
    score.add_argument(
        "--json-report",
        type=Path,
        default=ROOT / "evals" / "reports" / "baseline_v1.json",
    )
    score.add_argument(
        "--markdown-report",
        type=Path,
        default=ROOT / "evals" / "reports" / "baseline_v1.md",
    )
    score.set_defaults(func=command_score)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
