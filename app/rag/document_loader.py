"""知识文档加载与分块.

借鉴参考项目的文件加载 + MD5 去重 + 递归字符分块，并做标题感知增强：
- Markdown：先按标题层级（#/##/###）切出章节，章节标题写入 metadata.section，
  检索来源可显示"文件名 · 章节标题"（引用更精确，检索段落语义更完整）
- PDF：pypdf 按页提取文本，metadata.page 记录页码
- TXT：整篇读取后字符级分块
"""

import hashlib
from io import BytesIO
from pathlib import Path

import pdfplumber
from docx import Document as DocxDocument
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from pypdf import PdfReader

from app.core.config import settings
from app.core.logging import logger

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}

# 对话上传文件分析支持的格式与单文件上限（字符数截断在接口层做）
SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}

# 中文友好分隔符：优先段落/换行，其次句读，最后字符级兜底
_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "，", " "]

# Markdown 标题层级 -> metadata 键
_MD_HEADERS_TO_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]

# 上传文件分析：超出配置长度时截断，避免超出模型上下文与拖慢响应
UPLOAD_TEXT_MAX_CHARS = 6000


def compute_file_md5(file_path: Path) -> str:
    """计算文件内容的 MD5，用于摄取去重."""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            md5.update(chunk)
    return md5.hexdigest()


def list_knowledge_files(directory: Path) -> list[Path]:
    """递归列出目录下支持的文档文件（.md/.txt/.pdf），按路径排序保证摄取顺序稳定."""
    if not directory.is_dir():
        return []
    files: list[Path] = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(directory.rglob(f"*{ext}"))
    return sorted(files)


def _section_label(metadata: dict) -> str:
    """从 MarkdownHeaderSplitter 的 metadata 组出"一级 > 二级"章节标签."""
    return " > ".join(metadata[h] for h in ("h1", "h2", "h3") if metadata.get(h))


def _extract_pdf_pages(data: bytes) -> list[str]:
    """提取 PDF 每页文本：pdfplumber（版面感知、中文简历更稳）优先，pypdf 兜底.

    返回每页文本列表（空文本页保留为空串，调用方过滤）。
    """
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            pages = [(page.extract_text() or "").strip() for page in pdf.pages]
        if any(pages):
            return pages
        logger.warning("pdfplumber_extraction_empty_fallback_pypdf")
    except Exception as e:
        logger.warning("pdfplumber_extraction_failed_fallback_pypdf", error=str(e))
    reader = PdfReader(BytesIO(data))
    return [(page.extract_text() or "").strip() for page in reader.pages]


def _extract_docx_sections(data: bytes) -> list[tuple[str, str]]:
    """提取 docx 为 (章节标题, 内容) 列表，标题段由 Heading/标题 样式识别.

    与 Markdown 的"标题感知分块"约定一致：标题段进入 metadata.section，
    检索来源可显示"文件名 · 章节标题"；无标题的文档整篇作为一个空标题段。
    """
    doc = DocxDocument(BytesIO(data))
    sections: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style_name = (para.style.name or "").lower()
        if style_name.startswith("heading") or style_name.startswith("标题"):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines)))
                current_lines = []
            current_title = text
        else:
            current_lines.append(text)
    if current_lines:
        sections.append((current_title, "\n".join(current_lines)))
    return sections


def load_documents(file_path: Path) -> list[Document]:
    """读取文档为带元数据的 Document 列表（md 按标题分节、pdf 按页、txt 整篇、docx 按标题分节）."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        pages = _extract_pdf_pages(file_path.read_bytes())
        return [
            Document(
                page_content=text,
                metadata={"source": file_path.name, "page": index + 1},
            )
            for index, text in enumerate(pages)
            if text
        ]

    if suffix == ".docx":
        sections = _extract_docx_sections(file_path.read_bytes())
        return [
            Document(
                page_content=content,
                metadata={"source": file_path.name, "section": title} if title else {"source": file_path.name},
            )
            for title, content in sections
            if content
        ]

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read().strip()
    if not text:
        return []

    if suffix == ".md":
        header_docs = MarkdownHeaderTextSplitter(
            headers_to_split_on=_MD_HEADERS_TO_SPLIT_ON, strip_headers=False
        ).split_text(text)
        return [
            Document(
                page_content=doc.page_content,
                metadata={"source": file_path.name, "section": _section_label(doc.metadata)},
            )
            for doc in header_docs
        ]

    return [Document(page_content=text, metadata={"source": file_path.name})]


def split_documents(documents: list[Document]) -> list[Document]:
    """对超长文档（章节/页面）做字符级分块，保留 section/page 元数据."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        separators=_SEPARATORS,
        length_function=len,
    )
    return splitter.split_documents(documents)


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    """从上传文件的字节内容提取纯文本（对话文件分析用）.

    支持 .pdf（pypdf 逐页提取）、.docx（python-docx 按段落提取）、.txt/.md（UTF-8 解码）；
    其他格式抛 ValueError。
    """
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "\n".join(page for page in _extract_pdf_pages(data) if page).strip()
    if suffix == ".docx":
        return "\n".join(content for _, content in _extract_docx_sections(data) if content).strip()
    if suffix in (".txt", ".md"):
        return data.decode("utf-8", errors="replace").strip()
    raise ValueError(f"不支持的文件格式: {suffix or '未知'}，支持 PDF / TXT / MD / DOCX")
