"""Download public policy documents from https://policy.vinuni.edu.vn.

The crawler discovers policy pages from WordPress sitemaps, extracts public
attachments (PDF, Word, and Excel), and keeps a manifest so reruns do not
download unchanged files. Documents that redirect to authentication systems
such as SharePoint are intentionally skipped.

Examples:
    python src/crawl/vinuni_policy_crawler.py
    python src/crawl/vinuni_policy_crawler.py --output data/vinuni-policies
    python src/crawl/vinuni_policy_crawler.py --dry-run --max-pages 20
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import logging
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


BASE_URL = "https://policy.vinuni.edu.vn"
DEFAULT_OUTPUT = Path("data") / "vinuni-policies"
DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".odt",
    ".ods",
    ".rtf",
    ".csv",
    ".zip",
}
DOCUMENT_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/rtf": ".rtf",
    "text/csv": ".csv",
    "application/zip": ".zip",
}
AUTH_HOST_MARKERS = (
    "login.microsoftonline.com",
    "login.live.com",
    "sharepoint.com",
)
USER_AGENT = (
    "VinUniPolicyResearchCrawler/1.0 "
    "(public-policy-archival; +https://policy.vinuni.edu.vn)"
)


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.lower() not in {"a", "iframe", "embed", "object"}:
            return
        attributes = dict(attrs)
        value = attributes.get("href") or attributes.get("src") or attributes.get("data")
        if value:
            self.links.append(value)


@dataclass
class ManifestEntry:
    url: str
    source_page: str
    local_path: str
    content_type: str
    size: int
    sha256: str
    etag: str | None
    last_modified: str | None
    downloaded_at: str


class CrawlerError(RuntimeError):
    pass


class VinUniPolicyCrawler:
    def __init__(
        self,
        base_url: str,
        output_dir: Path,
        workers: int = 4,
        timeout: float = 30,
        delay: float = 0.25,
        dry_run: bool = False,
        max_pages: int | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.base_host = urllib.parse.urlsplit(self.base_url).netloc.lower()
        self.output_dir = output_dir.resolve()
        self.documents_dir = self.output_dir / "documents"
        self.manifest_path = self.output_dir / "manifest.json"
        self.workers = max(1, workers)
        self.timeout = timeout
        self.delay = max(0, delay)
        self.dry_run = dry_run
        self.max_pages = max_pages
        self.opener = urllib.request.build_opener()
        self.opener.addheaders = [
            ("User-Agent", USER_AGENT),
            ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
            ("Accept-Language", "en-US,en;q=0.9"),
        ]
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> dict[str, dict]:
        if not self.manifest_path.exists():
            return {}
        try:
            content = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            return {item["url"]: item for item in content.get("documents", [])}
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logging.warning("Ignoring invalid manifest %s: %s", self.manifest_path, exc)
            return {}

    def _request(self, url: str, headers: dict[str, str] | None = None):
        request = urllib.request.Request(url, headers=headers or {})
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return self.opener.open(request, timeout=self.timeout)
            except urllib.error.HTTPError:
                raise
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2**attempt)
        raise CrawlerError(f"Unable to fetch {url}: {last_error}")

    def _read_url(self, url: str) -> tuple[bytes, str, str]:
        with self._request(url) as response:
            final_url = response.geturl()
            content_type = response.headers.get_content_type()
            body = response.read()
        if "text/html" in content_type and b"cf-chl-" in body[:200_000]:
            raise CrawlerError(
                "Cloudflare challenge detected. Retry later or from a browser-approved network."
            )
        return body, content_type, final_url

    def _sitemap_urls(self) -> list[str]:
        queue = [
            f"{self.base_url}/wp-sitemap.xml",
            f"{self.base_url}/sitemap_index.xml",
            f"{self.base_url}/sitemap.xml",
        ]
        visited: set[str] = set()
        pages: set[str] = set()
        found_sitemap = False

        while queue:
            sitemap_url = queue.pop(0)
            if sitemap_url in visited:
                continue
            visited.add(sitemap_url)
            try:
                body, _, _ = self._read_url(sitemap_url)
                root = ET.fromstring(body)
            except (CrawlerError, urllib.error.HTTPError, ET.ParseError) as exc:
                logging.debug("Cannot read sitemap %s: %s", sitemap_url, exc)
                continue

            found_sitemap = True
            locations = [
                (node.text or "").strip()
                for node in root.iter()
                if node.tag.rsplit("}", 1)[-1] == "loc" and node.text
            ]
            if root.tag.rsplit("}", 1)[-1] == "sitemapindex":
                queue.extend(url for url in locations if url not in visited)
            else:
                pages.update(url for url in locations if self._is_internal_page(url))

        if not found_sitemap:
            logging.warning("No sitemap available; falling back to link crawling.")
            return self._crawl_page_urls()
        return sorted(pages)

    def _crawl_page_urls(self) -> list[str]:
        queue = [self.base_url + "/", f"{self.base_url}/all-policies/"]
        visited: set[str] = set()
        while queue and (self.max_pages is None or len(visited) < self.max_pages):
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                body, content_type, final_url = self._read_url(url)
            except (CrawlerError, urllib.error.HTTPError) as exc:
                logging.warning("%s", exc)
                continue
            if content_type != "text/html":
                continue
            for link in self._extract_links(body, final_url):
                if self._is_internal_page(link) and link not in visited:
                    queue.append(link)
            time.sleep(self.delay)
        return sorted(visited)

    def _is_internal_page(self, url: str) -> bool:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != self.base_host:
            return False
        return Path(parsed.path).suffix.lower() not in DOCUMENT_EXTENSIONS

    @staticmethod
    def _extract_links(body: bytes, page_url: str) -> list[str]:
        parser = LinkParser()
        parser.feed(body.decode("utf-8", errors="replace"))
        result: list[str] = []
        for raw_link in parser.links:
            link = urllib.parse.urljoin(page_url, raw_link)
            parsed = urllib.parse.urlsplit(link)
            if parsed.scheme in {"http", "https"}:
                result.append(urllib.parse.urlunsplit(parsed._replace(fragment="")))
        return result

    @staticmethod
    def _looks_like_document(url: str) -> bool:
        path = urllib.parse.unquote(urllib.parse.urlsplit(url).path)
        return Path(path).suffix.lower() in DOCUMENT_EXTENSIONS

    def discover_documents(self) -> dict[str, str]:
        pages = self._sitemap_urls()
        policy_pages = [
            page
            for page in pages
            if "/wp-content/" not in page and not self._looks_like_document(page)
        ]
        if self.max_pages is not None:
            policy_pages = policy_pages[: self.max_pages]
        logging.info("Inspecting %d pages", len(policy_pages))
        documents: dict[str, str] = {}

        def inspect(page_url: str) -> tuple[str, list[str]]:
            try:
                body, content_type, final_url = self._read_url(page_url)
                if content_type != "text/html":
                    return page_url, []
                return page_url, [
                    link
                    for link in self._extract_links(body, final_url)
                    if self._looks_like_document(link)
                ]
            except (CrawlerError, urllib.error.HTTPError) as exc:
                logging.warning("%s", exc)
                return page_url, []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as pool:
            for source_page, links in pool.map(inspect, policy_pages):
                for link in links:
                    documents.setdefault(link, source_page)
                if self.delay:
                    time.sleep(self.delay)
        return documents

    @staticmethod
    def _safe_filename(url: str) -> str:
        parsed = urllib.parse.urlsplit(url)
        filename = urllib.parse.unquote(Path(parsed.path).name)
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename).strip(" .")
        if not filename:
            filename = hashlib.sha256(url.encode()).hexdigest()[:16]
        stem, suffix = os.path.splitext(filename)
        if len(filename) > 180:
            filename = f"{stem[:140]}-{hashlib.sha256(url.encode()).hexdigest()[:10]}{suffix}"
        return filename

    def _unique_path(self, url: str) -> Path:
        filename = self._safe_filename(url)
        candidate = self.documents_dir / filename
        existing = self.manifest.get(url)
        if existing:
            return self.output_dir / existing["local_path"]
        if candidate.exists():
            stem, suffix = candidate.stem, candidate.suffix
            candidate = candidate.with_name(
                f"{stem}-{hashlib.sha256(url.encode()).hexdigest()[:10]}{suffix}"
            )
        return candidate

    def download_document(self, url: str, source_page: str) -> ManifestEntry | None:
        host = urllib.parse.urlsplit(url).netloc.lower()
        if any(marker in host for marker in AUTH_HOST_MARKERS):
            logging.info("Skipping authenticated document: %s", url)
            return None
        if self.dry_run:
            logging.info("[dry-run] %s", url)
            return None

        target = self._unique_path(url)
        old = self.manifest.get(url, {})
        conditional_headers: dict[str, str] = {}
        if target.exists() and old.get("etag"):
            conditional_headers["If-None-Match"] = old["etag"]
        if target.exists() and old.get("last_modified"):
            conditional_headers["If-Modified-Since"] = old["last_modified"]

        try:
            response = self._request(url, conditional_headers)
        except CrawlerError as exc:
            logging.error("%s", exc)
            return None
        except urllib.error.HTTPError as exc:
            if exc.code == 304 and old:
                logging.info("Unchanged: %s", target.name)
                return ManifestEntry(**old)
            logging.error("HTTP %s for %s", exc.code, url)
            return None

        with response:
            final_url = response.geturl()
            final_host = urllib.parse.urlsplit(final_url).netloc.lower()
            if any(marker in final_host for marker in AUTH_HOST_MARKERS):
                logging.info("Skipping authenticated redirect: %s", final_url)
                return None
            content_type = response.headers.get_content_type()
            if content_type == "text/html":
                logging.warning("Skipping HTML response instead of a document: %s", url)
                return None
            expected_ext = DOCUMENT_CONTENT_TYPES.get(content_type)
            if expected_ext and not target.suffix:
                target = target.with_suffix(expected_ext)

            self.documents_dir.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            size = 0
            fd, temp_name = tempfile.mkstemp(
                prefix=".download-", dir=str(self.documents_dir)
            )
            try:
                with os.fdopen(fd, "wb") as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                os.replace(temp_name, target)
            except Exception:
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass
                raise

            entry = ManifestEntry(
                url=url,
                source_page=source_page,
                local_path=target.relative_to(self.output_dir).as_posix(),
                content_type=content_type,
                size=size,
                sha256=digest.hexdigest(),
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
                downloaded_at=datetime.now(timezone.utc).isoformat(),
            )
            logging.info("Downloaded %s (%d bytes)", target.name, size)
            return entry

    def _save_manifest(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "base_url": self.base_url,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "documents": sorted(self.manifest.values(), key=lambda item: item["url"]),
        }
        temp_path = self.manifest_path.with_suffix(".json.tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temp_path, self.manifest_path)

    def run(self) -> int:
        documents = self.discover_documents()
        logging.info("Found %d public document links", len(documents))
        if self.dry_run:
            for url in sorted(documents):
                logging.info("[dry-run] %s", url)
            return 0

        failures = 0
        for url, source_page in sorted(documents.items()):
            try:
                entry = self.download_document(url, source_page)
                if entry:
                    self.manifest[url] = asdict(entry)
                else:
                    failures += 1
            except Exception as exc:  # keep a bulk crawl progressing
                failures += 1
                logging.error("Failed to download %s: %s", url, exc)
            self._save_manifest()
            time.sleep(self.delay)
        logging.info(
            "Finished: %d documents in manifest, %d skipped/failed",
            len(self.manifest),
            failures,
        )
        return 1 if failures and not self.manifest else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download public documents from the VinUni policy website."
    )
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    crawler = VinUniPolicyCrawler(
        base_url=args.base_url,
        output_dir=args.output,
        workers=args.workers,
        timeout=args.timeout,
        delay=args.delay,
        dry_run=args.dry_run,
        max_pages=args.max_pages,
    )
    try:
        return crawler.run()
    except KeyboardInterrupt:
        logging.warning("Interrupted")
        return 130
    except CrawlerError as exc:
        logging.error("%s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
