"""Run read-only golden cases against the deployed Agent HTTP API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.api_runner import (
    APIEvaluationError,
    AgentAPIClient,
    build_failed_result,
    build_result,
    ensure_read_only_cases,
    parse_case_ids,
)
from evals.eval_core import load_jsonl, validate_cases
from evals.run_eval import command_score


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "evals" / "cases" / "golden_v1.jsonl"
DEFAULT_RESULTS = ROOT / "evals" / "results" / "api_v1.jsonl"
DEFAULT_JSON_REPORT = ROOT / "evals" / "reports" / "api_v1.json"
DEFAULT_MARKDOWN_REPORT = ROOT / "evals" / "reports" / "api_v1.md"


def _load_selected_cases(path: Path, expression: str) -> list[dict]:
    cases = load_jsonl(path)
    errors = validate_cases(cases)
    if errors:
        raise ValueError("\n".join(errors))
    case_map = {case["id"]: case for case in cases}
    selected_ids = parse_case_ids(expression, case_map)
    selected = [case_map[case_id] for case_id in selected_ids]
    ensure_read_only_cases(selected)
    return selected


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records),
        encoding="utf-8",
    )


def command_run(args: argparse.Namespace) -> int:
    selected = _load_selected_cases(args.cases, args.case_ids)
    if args.output.exists() and not args.force:
        raise ValueError(
            f"结果文件已存在：{args.output}；如需覆盖请显式传入 --force"
        )

    records: list[dict] = []
    total = len(selected) * args.runs
    sequence = 0
    for run_number in range(1, args.runs + 1):
        for case in selected:
            sequence += 1
            print(
                f"[{sequence}/{total}] {case['id']} 第 {run_number} 次：{case['title']}",
                flush=True,
            )
            try:
                client = AgentAPIClient(args.base_url, args.timeout)
                user = client.create_demo_session()
                trace, latency_ms = client.run_case(case["input"]["message"])
                result = build_result(case, run_number, trace, latency_ms)
                print(
                    f"  完成：{latency_ms} ms，工具 {len(result['tool_calls'])} 个，"
                    f"用户 {str(user.get('user_id', ''))[:12]}…",
                    flush=True,
                )
            except APIEvaluationError as exc:
                result = build_failed_result(case, run_number, str(exc))
                print(f"  失败：{exc}", flush=True)
            records.append(result)

    _write_jsonl(args.output, records)
    print(f"结果已写入：{args.output}", flush=True)

    score_args = argparse.Namespace(
        cases=args.cases,
        results=args.output,
        json_report=args.json_report,
        markdown_report=args.markdown_report,
    )
    return command_score(score_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="卡营智控 Agent 只读 API 自动评测")
    parser.add_argument("--base-url", required=True, help="Agent Web 根地址")
    parser.add_argument("--case-ids", default="E001-E005", help="例如 E001-E005")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--runs", type=int, default=1, choices=range(1, 6))
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument(
        "--markdown-report", type=Path, default=DEFAULT_MARKDOWN_REPORT
    )
    parser.add_argument(
        "--force", action="store_true", help="显式覆盖已经存在的结果文件"
    )
    parser.set_defaults(func=command_run)
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
