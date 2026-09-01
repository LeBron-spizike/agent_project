"""知识库检索单条查询诊断工具.

直接查看某个问题的向量检索命中结果与相似度得分（不经过 LLM），
用于判断"召回准不准"和选定 RAG_SCORE_THRESHOLD 阈值。

用法：
    uv run python -m app.rag.query "怎么写简历的项目经历"
    uv run python -m app.rag.query "怎么写简历" --k 6
"""

import argparse
import asyncio

from rich.console import Console
from rich.table import Table

from app.rag.rag_service import rag_service


async def run_query(question: str, k: int | None) -> None:
    """执行单条检索并用 rich 表格输出得分与来源."""
    console = Console()
    chunks = await rag_service.search(question, k=k)
    if not chunks:
        console.print("[yellow]未检索到任何分块（知识库为空、RAG_ENABLED=false 或检索失败）[/yellow]")
        return

    table = Table(title=f"检索结果：{question}")
    table.add_column("得分", justify="right", style="cyan")
    table.add_column("来源文档", style="green")
    table.add_column("内容预览")
    for chunk in chunks:
        label = f"{chunk.source} · {chunk.section}" if chunk.section else chunk.source
        preview = chunk.content[:60].replace("\n", " ")
        table.add_row(f"{chunk.score:.3f}", label, preview)
    console.print(table)
    console.print("得分 = 1 - 余弦距离，范围 0~1，越高越相关；据此可设定 RAG_SCORE_THRESHOLD 过滤阈值")


def main() -> None:
    """解析命令行参数并执行诊断查询."""
    parser = argparse.ArgumentParser(description="知识库检索诊断查询")
    parser.add_argument("question", help="要测试的问题")
    parser.add_argument("--k", type=int, default=None, help="返回条数，缺省使用 RAG_TOP_K")
    args = parser.parse_args()
    asyncio.run(run_query(args.question, args.k))


if __name__ == "__main__":
    main()
