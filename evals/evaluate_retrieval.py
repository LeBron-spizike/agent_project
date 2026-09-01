"""知识库检索质量评测.

借鉴参考项目 rag/evaluate_retrieval.py 的指标体系，对 evals/retrieval_eval.jsonl 评测集
计算 hit@k / source_hit@k / precision@k / keyword_recall@k / mrr@k，rich 表格输出。

用法：
    uv run python evals/evaluate_retrieval.py
    uv run python evals/evaluate_retrieval.py --eval-file evals/retrieval_eval.jsonl --k 3 5
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from rich.console import Console
from rich.table import Table

# 脚本直接运行时项目根目录不在 sys.path，先插入再导入 app 包
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.rag.rag_service import rag_service  # noqa: E402

DEFAULT_EVAL_FILE = Path("evals/retrieval_eval.jsonl")


@dataclass
class EvalCase:
    """单条检索评测用例."""

    id: str
    query: str
    category: str
    expected_sources: list[str] = field(default_factory=list)
    expected_keywords: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    """单个 k 值下的评测指标."""

    k: int
    hit: float
    source_hit: float
    precision: float
    keyword_recall: float
    mrr: float
    misses: list[str] = field(default_factory=list)


def load_eval_cases(eval_file: Path) -> list[EvalCase]:
    """从 JSONL 文件加载评测用例，逐行校验 JSON 格式."""
    cases: list[EvalCase] = []
    with open(eval_file, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                cases.append(
                    EvalCase(
                        id=str(item["id"]),
                        query=str(item["query"]),
                        category=str(item.get("category", "unknown")),
                        expected_sources=[str(s) for s in item.get("expected_sources", [])],
                        expected_keywords=[str(k) for k in item.get("expected_keywords", [])],
                    )
                )
            except (KeyError, json.JSONDecodeError) as e:
                raise ValueError(f"评测集第 {line_no} 行格式错误: {e}") from e
    return cases


def chunk_matches_case(chunk_content: str, chunk_source: str, case: EvalCase) -> bool:
    """判断单条检索结果是否命中用例：来源匹配且内容包含任一期望关键词."""
    source_hit = any(name in chunk_source for name in case.expected_sources)
    keyword_hit = any(keyword in chunk_content for keyword in case.expected_keywords)
    return source_hit and keyword_hit if case.expected_sources else keyword_hit


def keyword_recall(chunks_content: Iterable[str], case: EvalCase) -> float:
    """期望关键词在全部检索结果中的覆盖率."""
    if not case.expected_keywords:
        return 0.0
    joined = "\n".join(chunks_content)
    matched = sum(1 for keyword in case.expected_keywords if keyword in joined)
    return matched / len(case.expected_keywords)


async def evaluate_at_k(cases: list[EvalCase], k: int) -> EvalResult:
    """在指定 k 值下评测全部用例并汇总指标."""
    total = len(cases)
    hit_count = 0
    source_hit_count = 0
    precision_sum = 0.0
    keyword_recall_sum = 0.0
    reciprocal_rank_sum = 0.0
    misses: list[str] = []

    for case in cases:
        chunks = await rag_service.search(case.query, k=k)
        contents = [chunk.content for chunk in chunks]
        sources = [chunk.source for chunk in chunks]

        relevance = [
            chunk_matches_case(content, source, case)
            for content, source in zip(contents, sources, strict=True)
        ]
        first_rank = next((idx + 1 for idx, is_relevant in enumerate(relevance) if is_relevant), None)

        hit_count += int(any(relevance))
        source_hit_count += int(
            bool(case.expected_sources) and any(any(name in s for name in case.expected_sources) for s in sources)
        )
        precision_sum += sum(relevance) / k if k else 0.0
        keyword_recall_sum += keyword_recall(contents, case)
        reciprocal_rank_sum += 1 / first_rank if first_rank else 0.0

        if not any(relevance):
            misses.append(f"{case.id}: {case.query}")

    return EvalResult(
        k=k,
        hit=hit_count / total if total else 0.0,
        source_hit=source_hit_count / total if total else 0.0,
        precision=precision_sum / total if total else 0.0,
        keyword_recall=keyword_recall_sum / total if total else 0.0,
        mrr=reciprocal_rank_sum / total if total else 0.0,
        misses=misses,
    )


def print_results(console: Console, results: list[EvalResult], show_misses: int) -> None:
    """用 rich 表格输出各 k 值指标与未命中用例."""
    table = Table(title="知识库检索质量评测")
    for column in ("指标", *[f"@{result.k}" for result in results]):
        table.add_column(column)

    rows = [
        ("hit", lambda r: r.hit),
        ("source_hit", lambda r: r.source_hit),
        ("precision", lambda r: r.precision),
        ("keyword_recall", lambda r: r.keyword_recall),
        ("mrr", lambda r: r.mrr),
    ]
    for label, getter in rows:
        table.add_row(label, *[f"{getter(result):.2%}" for result in results])
    console.print(table)

    if show_misses:
        for result in results:
            if result.misses:
                console.print(f"[yellow]未命中用例（@{result.k}，前 {show_misses} 条）[/yellow]")
                for miss in result.misses[:show_misses]:
                    console.print(f"  - {miss}")


async def run_evaluation(eval_file: Path, k_values: list[int], show_misses: int) -> list[EvalResult]:
    """加载评测集并逐 k 值评测."""
    cases = load_eval_cases(eval_file)
    console = Console()
    console.print(f"加载 {len(cases)} 条评测用例：{eval_file}")
    results = [await evaluate_at_k(cases, k) for k in k_values]
    print_results(console, results, show_misses)
    return results


def main() -> None:
    """解析命令行参数并执行评测."""
    parser = argparse.ArgumentParser(description="知识库检索质量评测")
    parser.add_argument("--eval-file", type=Path, default=DEFAULT_EVAL_FILE, help="评测集 JSONL 路径")
    parser.add_argument("--k", type=int, nargs="+", default=[3, 5], help="要评测的 top-k 值")
    parser.add_argument("--show-misses", type=int, default=5, help="每个 k 值打印的未命中用例数")
    # rerank 对比：默认沿用配置 RAG_RERANK_ENABLED；--rerank / --no-rerank 强制开/关（注意 settings 是运行时可改的普通对象）
    parser.add_argument("--rerank", dest="rerank", action="store_true", default=None, help="强制开启 rerank 精排")
    parser.add_argument("--no-rerank", dest="rerank", action="store_false", help="强制关闭 rerank 精排（纯向量）")
    args = parser.parse_args()

    if args.rerank is not None:
        settings.RAG_RERANK_ENABLED = args.rerank
    Console().print(
        f"rerank 状态: {'开启（gte-rerank）' if settings.RAG_RERANK_ENABLED else '关闭（纯向量）'}"
    )
    asyncio.run(run_evaluation(args.eval_file, args.k, args.show_misses))


if __name__ == "__main__":
    main()
