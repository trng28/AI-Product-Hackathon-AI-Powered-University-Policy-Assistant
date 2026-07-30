"""Convert archived VinUni HTML into clean, inspectable RAG data.

Examples:
    python crawl/process_vinuni_raw.py
    python crawl/process_vinuni_raw.py --input data/vinuni-policies
    python crawl/process_vinuni_raw.py --chunk-size 1600 --chunk-overlap 200
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, NavigableString, Tag
from ftfy import fix_text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt",
    ".ods", ".rtf", ".csv", ".zip",
}


@dataclass
class ProcessedPage:
    id: str
    url: str
    title: str
    page_type: str
    category: str
    text: str
    metadata: dict[str, str]
    tables: list[dict]
    document_links: list[str]
    external_links: list[str]
    source_html: str
    content_sha256: str
    is_public: bool
    exclusion_reason: str


def _default_input() -> Path:
    candidates = [
        Path.cwd() / "data" / "vinuni-policies",
        PROJECT_ROOT / "data" / "vinuni-policies",
        PROJECT_ROOT / "src" / "data" / "vinuni-policies",
    ]
    for candidate in candidates:
        if (candidate / "raw" / "manifest.json").exists():
            return candidate
    return candidates[0]


def _cell_text(cell: Tag) -> str:
    return re.sub(r"\s+", " ", fix_text(cell.get_text(" ", strip=True))).strip()


def _table_data(table: Tag, index: int) -> dict:
    grid: dict[tuple[int, int], str] = {}
    source_rows = [
        row
        for row in table.find_all("tr")
        if row.find_parent("table") is table
    ]
    header_rows = 0
    for row_index, row in enumerate(source_rows):
        cells = row.find_all(["th", "td"], recursive=False)
        if cells and all(cell.name == "th" for cell in cells):
            header_rows += 1
        column = 0
        for cell in cells:
            while (row_index, column) in grid:
                column += 1
            try:
                rowspan = max(1, int(cell.get("rowspan", 1)))
                colspan = max(1, int(cell.get("colspan", 1)))
            except (TypeError, ValueError):
                rowspan = colspan = 1
            value = _cell_text(cell)
            for row_offset in range(rowspan):
                for column_offset in range(colspan):
                    grid[(row_index + row_offset, column + column_offset)] = value
            column += colspan

    row_count = max((position[0] for position in grid), default=-1) + 1
    column_count = max((position[1] for position in grid), default=-1) + 1
    rows = [
        [grid.get((row, column), "") for column in range(column_count)]
        for row in range(row_count)
    ]
    caption_node = table.find("caption")
    return {
        "index": index,
        "caption": _cell_text(caption_node) if isinstance(caption_node, Tag) else "",
        "header_rows": header_rows,
        "columns": column_count,
        "rows": rows,
    }


def _markdown_table(table: dict) -> str:
    rows = table["rows"]
    if not rows:
        return ""

    def render(row: list[str]) -> str:
        values = [
            value.replace("|", "\\|").replace("\n", "<br>")
            for value in row
        ]
        return "| " + " | ".join(values) + " |"

    lines = []
    if table["caption"]:
        lines.append(f"**{table['caption']}**")
    lines.append(render(rows[0]))
    lines.append("| " + " | ".join("---" for _ in rows[0]) + " |")
    lines.extend(render(row) for row in rows[1:])
    return "\n".join(lines)


def _extract_tables(element: Tag | BeautifulSoup | None) -> list[dict]:
    if element is None:
        return []
    return [
        _table_data(table, index)
        for index, table in enumerate(element.find_all("table"), start=1)
        if table.find_parent("table") is None
        or table.find_parent("table") not in element.find_all("table")
    ]


def _clean_text(element: Tag | BeautifulSoup | None) -> str:
    if element is None:
        return ""
    clone = BeautifulSoup(str(element), "html.parser")
    for index, table_node in enumerate(clone.find_all("table"), start=1):
        if table_node.find_parent("table") is not None:
            continue
        table_node.replace_with(
            NavigableString(f"\n\n{_markdown_table(_table_data(table_node, index))}\n\n")
        )
    for unwanted in clone.select(
        "script, style, noscript, svg, form, nav, footer, header, "
        ".menu_single_sidebar, .breadcrumbs"
    ):
        unwanted.decompose()
    lines = []
    for raw_line in clone.get_text("\n", strip=True).splitlines():
        line = re.sub(r"\s+", " ", fix_text(raw_line)).strip()
        if line.casefold() == "top of page":
            continue
        if line and (not lines or line != lines[-1]):
            lines.append(line)
    return "\n".join(lines)


def _canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit(parsed._replace(fragment=""))


def _links(soup: BeautifulSoup, page_url: str) -> tuple[list[str], list[str]]:
    documents: set[str] = set()
    external: set[str] = set()
    page_host = urlsplit(page_url).netloc.lower()
    for anchor in soup.select("a[href]"):
        url = _canonical_url(urljoin(page_url, str(anchor.get("href", ""))))
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if Path(parsed.path).suffix.lower() in DOCUMENT_EXTENSIONS:
            documents.add(url)
        elif parsed.netloc.lower() != page_host:
            external.add(url)
    return sorted(documents), sorted(external)


def _metadata(soup: BeautifulSoup) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in soup.select("#status_details .status_item"):
        label_node = item.select_one("h4")
        value_node = item.select_one(".p-2, .col-8, .col-lg-9")
        label = _clean_text(label_node).rstrip(":")
        value = _clean_text(value_node)
        if label and value:
            key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
            result[key] = value
    return result


def _category(soup: BeautifulSoup) -> str:
    crumbs = [
        _clean_text(node)
        for node in soup.select(".breadcrumbs a, .breadcrumbs .current")
    ]
    useful = [crumb for crumb in crumbs if crumb and crumb.lower() != "home"]
    return useful[-2] if len(useful) >= 2 else ""


def parse_page(
    html: str, item: dict, input_dir: Path, internal_urls: set[str]
) -> ProcessedPage:
    soup = BeautifulSoup(html, "html.parser")
    policy_root = soup.select_one("section.single_policy")
    title_node = soup.select_one("h1.single_title, main h1, h1")
    title = _clean_text(title_node)
    if not title and soup.title:
        title = re.sub(r"\s*[|–-]\s*VinUni.*$", "", soup.title.get_text(strip=True))
    title = title or item["url"].rstrip("/").rsplit("/", 1)[-1] or "VinUni Policies"

    metadata = _metadata(soup) if policy_root else {}
    if policy_root:
        content_node = soup.select_one("#single_current_version article.single_content")
        tables = _extract_tables(content_node)
        content = _clean_text(content_node)
        status = _clean_text(soup.select_one("#status_details"))
        text = "\n\n".join(part for part in (content, status) if part)
        page_type = "policy"
    else:
        content_node = soup.select_one("main") or soup.body
        tables = _extract_tables(content_node)
        text = _clean_text(content_node)
        page_type = "page"

    document_links, external_links = _links(soup, item["url"])
    title_has_internal_marker = bool(re.search(r"\(\s*\*\s*\)", title))
    is_internal = _canonical_url(item["url"]) in internal_urls or title_has_internal_marker
    identity = hashlib.sha1(item["url"].encode("utf-8")).hexdigest()[:16]
    return ProcessedPage(
        id=identity,
        url=item["url"],
        title=title,
        page_type=page_type,
        category=_category(soup),
        text=text,
        metadata=metadata,
        tables=tables,
        document_links=document_links,
        external_links=external_links,
        source_html=str(
            (input_dir / item["local_path"]).relative_to(input_dir).as_posix()
        ),
        content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        is_public=not is_internal,
        exclusion_reason=(
            "Title is marked (*) as an internal VinUni document"
            if is_internal
            else ""
        ),
    )


def _chunks(text: str, size: int, overlap: int) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    units: list[str] = []
    table_header = ""
    for line in lines:
        is_table_row = line.startswith("| ") and line.endswith(" |")
        is_separator = is_table_row and not line.replace("|", "").replace("-", "").strip()
        if is_table_row and not table_header and not is_separator:
            table_header = line
        elif not is_table_row:
            table_header = ""

        if len(line) <= size:
            units.append(line)
            continue
        # Very wide table rows exceed embedding model limits. Split only those
        # rows and repeat the header so every continuation retains column context.
        prefix = f"{table_header}\n" if is_table_row and table_header != line else ""
        available = max(200, size - len(prefix))
        units.extend(
            f"{prefix}{line[start : start + available]}"
            for start in range(0, len(line), available)
        )

    chunks: list[str] = []
    current: list[str] = []
    for unit in units:
        candidate = "\n".join([*current, unit])
        if current and len(candidate) > size:
            chunks.append("\n".join(current))
            carry: list[str] = []
            carry_size = 0
            for previous in reversed(current):
                if carry_size + len(previous) + 1 > overlap:
                    break
                carry.insert(0, previous)
                carry_size += len(previous) + 1
            if carry and len("\n".join([*carry, unit])) > size:
                carry = []
            current = [*carry, unit]
        else:
            current.append(unit)
    if current:
        chunks.append("\n".join(current))
    return chunks


def _markdown(page: ProcessedPage) -> str:
    lines = [
        f"# {page.title}",
        "",
        f"- URL: {page.url}",
        f"- Category: {page.category or 'N/A'}",
    ]
    for key, value in page.metadata.items():
        lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    if page.document_links:
        lines.extend(["", "## Documents", ""])
        lines.extend(f"- {url}" for url in page.document_links)
    if page.external_links:
        lines.extend(["", "## External links", ""])
        lines.extend(f"- {url}" for url in page.external_links)
    lines.extend(["", "## Content", "", page.text, ""])
    return "\n".join(lines)


def process(input_dir: Path, output_dir: Path, chunk_size: int, overlap: int) -> dict:
    manifest_path = input_dir / "raw" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Raw manifest not found: {manifest_path}")
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_items = raw.get("pages", [])

    # The (*) marker exists on listing-page links, not necessarily in the H1 of
    # the linked detail page. Build the visibility map before parsing details.
    internal_urls: set[str] = set()
    for item in raw_items:
        path = input_dir / item["local_path"]
        try:
            listing_soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        except (OSError, KeyError):
            continue
        for anchor in listing_soup.select("a[href]"):
            marker = anchor.select_one("span.highlight")
            if marker and re.search(r"\(\s*\*\s*\)", marker.get_text(" ", strip=True)):
                internal_urls.add(
                    _canonical_url(
                        urljoin(item["url"], str(anchor.get("href", "")))
                    )
                )

    pages: list[ProcessedPage] = []
    failures: list[dict[str, str]] = []
    for item in raw_items:
        path = input_dir / item["local_path"]
        try:
            page = parse_page(
                path.read_text(encoding="utf-8"), item, input_dir, internal_urls
            )
            if page.text:
                pages.append(page)
            else:
                failures.append({"url": item["url"], "error": "empty extracted text"})
        except (OSError, KeyError, ValueError) as exc:
            failures.append({"url": item.get("url", ""), "error": str(exc)})

    all_policies = [page for page in pages if page.page_type == "policy"]
    policies = [page for page in all_policies if page.is_public]
    internal_policies = [page for page in all_policies if not page.is_public]
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir = output_dir / "markdown"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    public_markdown_ids = {page.id for page in policies}
    for stale_path in markdown_dir.glob("*.md"):
        if stale_path.stem not in public_markdown_ids:
            stale_path.unlink()

    def write_jsonl(path: Path, records: Iterable[dict]) -> None:
        path.write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
            encoding="utf-8",
        )

    write_jsonl(output_dir / "pages.jsonl", (asdict(page) for page in pages))
    write_jsonl(output_dir / "policies.jsonl", (asdict(page) for page in policies))
    write_jsonl(
        output_dir / "internal_policies.jsonl",
        (asdict(page) for page in internal_policies),
    )

    chunk_records = []
    for page in policies:
        for index, text in enumerate(_chunks(page.text, chunk_size, overlap), start=1):
            chunk_records.append(
                {
                    "id": f"{page.id}-{index:04d}",
                    "page_id": page.id,
                    "url": page.url,
                    "title": page.title,
                    "category": page.category,
                    "reference_number": page.metadata.get("reference_number", ""),
                    "document_type": page.metadata.get("document_type", ""),
                    "text": text,
                    "source_html": page.source_html,
                }
            )
        (markdown_dir / f"{page.id}.md").write_text(
            _markdown(page), encoding="utf-8"
        )
    write_jsonl(output_dir / "chunks.jsonl", chunk_records)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_manifest": str(manifest_path.resolve()),
        "pages": len(pages),
        "policies": len(policies),
        "internal_policies_excluded": len(internal_policies),
        "internal_urls_detected": len(internal_urls),
        "chunks": len(chunk_records),
        "failures": failures,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    default_input = _default_input()
    parser = argparse.ArgumentParser(
        description="Clean archived VinUni HTML and create RAG-ready JSONL chunks."
    )
    parser.add_argument("--input", type=Path, default=default_input)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--chunk-size", type=int, default=1600)
    parser.add_argument("--chunk-overlap", type=int, default=200)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    input_dir = args.input.resolve()
    output_dir = (
        args.output.resolve()
        if args.output
        else input_dir / "processed"
    )
    if args.chunk_size < 200:
        raise SystemExit("--chunk-size must be at least 200")
    if args.chunk_overlap < 0 or args.chunk_overlap >= args.chunk_size:
        raise SystemExit("--chunk-overlap must be >= 0 and smaller than --chunk-size")
    try:
        summary = process(
            input_dir, output_dir, args.chunk_size, args.chunk_overlap
        )
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logging.error("%s", exc)
        return 2
    logging.info(
        "Processed %d pages: %d public policies, %d internal excluded, "
        "%d chunks into %s",
        summary["pages"],
        summary["policies"],
        summary["internal_policies_excluded"],
        summary["chunks"],
        output_dir,
    )
    if summary["failures"]:
        logging.warning("%d pages could not be processed", len(summary["failures"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
