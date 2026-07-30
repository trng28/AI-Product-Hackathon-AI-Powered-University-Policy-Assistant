from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import PROJECT_ROOT, Settings
from .indexing import build_index
from .service import PolicyAssistant


def _print_answer(answer) -> None:
    print()
    print("TRẢ LỜI")
    print("─" * 72)
    print(answer.answer)
    print()
    confidence = round(answer.confidence * 100)
    evidence = "Đủ căn cứ" if answer.evidence_sufficient else "Chưa đủ căn cứ"
    print(f"Độ tin cậy: {confidence}% · {evidence}")
    if answer.citations:
        print()
        print("TRÍCH DẪN")
        for index, citation in enumerate(answer.citations, start=1):
            location = " · ".join(
                part
                for part in (
                    citation.get("article", ""),
                    citation.get("clause", ""),
                    f"Trang {citation.get('page')}",
                )
                if part
            )
            print(f"[{index}] {location}")
            print(f"    {citation.get('document', '')}")
            if citation.get("support"):
                print(f"    {citation['support']}")
    print()


def _chat() -> None:
    print()
    print("VinUni Policy Assistant · Multi-Agent RAG")
    print("Gõ /help để xem lệnh, /exit để kết thúc.")
    print("═" * 72)
    try:
        settings = Settings.from_env()
        required_files = (
            settings.index_dir / "config.json",
            settings.index_dir / "chunks.json",
            settings.index_dir / "vectors.faiss",
        )
        index_model = ""
        if required_files[0].is_file():
            try:
                index_model = json.loads(
                    required_files[0].read_text(encoding="utf-8")
                ).get("embedding_model", "")
            except (OSError, json.JSONDecodeError):
                pass
        if not all(path.is_file() for path in required_files) or (
            index_model != settings.embedding_model
        ):
            pdf_path = PROJECT_ROOT / "src" / "data" / (
                "VU_HT03.VN_QC-dao-tao-dai-hoc-he-chinh-quy-"
                "theo-he-thong-tin-chi.pdf"
            )
            if not pdf_path.is_file():
                raise FileNotFoundError(
                    "Knowledge index is missing and the bundled policy PDF was not found. "
                    "Run the `index` command with a PDF path."
                )
            print("Knowledge index chưa có hoặc dùng model cũ. Đang lập chỉ mục PDF mẫu...")
            count = build_index(
                [pdf_path], settings.index_dir, settings.embedding_model
            )
            print(f"Đã lập chỉ mục {count} legal chunks.\n")
        assistant = PolicyAssistant()
    except Exception as exc:
        raise SystemExit(f"Không thể khởi tạo assistant: {exc}") from exc

    while True:
        try:
            question = input("Bạn > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTạm biệt!")
            return
        if not question:
            continue
        command = question.lower()
        if command in {"/exit", "/quit", "exit", "quit"}:
            print("Tạm biệt!")
            return
        if command == "/help":
            print(
                "\n/help  Xem danh sách lệnh\n"
                "/clear Xóa màn hình\n"
                "/exit  Kết thúc phiên chat\n"
            )
            continue
        if command == "/clear":
            print("\033[2J\033[H", end="")
            continue
        try:
            print("Agent đang phân tích...", flush=True)
            _print_answer(assistant.ask(question))
        except Exception as exc:
            print(f"\nLỗi: {exc}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="VinUni Policy Assistant")
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index", help="Build the legal document index")
    index.add_argument("pdf", nargs="+", type=Path)
    index.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "data" / "policy-index"
    )
    index.add_argument(
        "--embedding-model", default="intfloat/multilingual-e5-base"
    )
    ask = commands.add_parser("ask", help="Ask a policy question")
    ask.add_argument("question")
    commands.add_parser("chat", help="Start an interactive chat session")
    args = parser.parse_args()

    if args.command == "index":
        count = build_index(args.pdf, args.output, args.embedding_model)
        print(f"Indexed {count} legal chunks into {args.output}")
    elif args.command == "ask":
        answer = PolicyAssistant().ask(args.question)
        _print_answer(answer)
    else:
        _chat()


if __name__ == "__main__":
    main()
