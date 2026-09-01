"""知识库摄取命令行入口.

用法：
    uv run python -m app.rag.ingest                 # 摄取 RAG_KNOWLEDGE_DIR
    uv run python -m app.rag.ingest --dir data/knowledge

用 rich 输出摄取报告表格，便于人工核对每个文件的处理结果。
"""

import argparse
import asyncio

from rich.console import Console
from rich.table import Table

from app.core.config import settings
from app.rag.rag_service import rag_service


async def run_ingest(directory: str | None, force: bool = False) -> None:
    """执行摄取并用 rich 表格输出报告."""
    console = Console()
    target = directory or settings.RAG_KNOWLEDGE_DIR
    hint = "（强制重摄）" if force else ""
    console.print(f"[bold cyan]RAG 知识库摄取[/bold cyan]{hint} 目录：{target}")

    await rag_service.initialize()
    report = await rag_service.ingest_directory(target, force=force)

    table = Table(title="摄取报告")
    table.add_column("结果", style="bold")
    table.add_column("文件")
    table.add_column("说明")

    for file_id in report.ingested_files:
        table.add_row("[green]ingested[/green]", file_id, "")
    for file_id in report.skipped_files:
        table.add_row("[yellow]skipped[/yellow]", file_id, "内容 MD5 未变化")
    for file_id in report.failed_files:
        table.add_row("[red]failed[/red]", file_id, report.failed_reasons.get(file_id, ""))

    console.print(table)
    console.print(
        f"共 {report.total_files} 个文件：成功 {len(report.ingested_files)}，"
        f"跳过 {len(report.skipped_files)}，失败 {len(report.failed_files)}，"
        f"新增分块 {report.total_chunks}"
    )


def main() -> None:
    """解析命令行参数并执行摄取."""
    parser = argparse.ArgumentParser(description="RAG 知识库摄取工具")
    parser.add_argument("--dir", default=None, help="知识目录，缺省使用 RAG_KNOWLEDGE_DIR")
    parser.add_argument(
        "--force",
        action="store_true",
        help="忽略 MD5 强制重新分块摄取（分块逻辑变更后使用，如启用标题分块/换 embedding 模型）",
    )
    args = parser.parse_args()
    asyncio.run(run_ingest(args.dir, force=args.force))


if __name__ == "__main__":
    main()
