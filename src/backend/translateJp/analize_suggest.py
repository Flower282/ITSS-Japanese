from pathlib import Path
import sys

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(override=True)

try:
    from src.backend.translateJp.api_clients import analyze_chat_history_file
except ModuleNotFoundError:
    from api_clients import analyze_chat_history_file


CURRENT_DIR = Path(__file__).resolve().parent
HISTORY_FILE = CURRENT_DIR / "history.txt"


def analyze_and_suggest_chat(file_path: str | Path = HISTORY_FILE):
    return analyze_chat_history_file(file_path)


def print_analysis(analysis: dict) -> None:
    print("--- NGỮ CẢNH ---")
    print(analysis["context_summary"])
    print("\n--- GỢI Ý CÂU TRẢ LỜI ---")
    for i, suggestion in enumerate(analysis["suggestions"], 1):
        romaji = suggestion.get("romaji")
        if romaji:
            print(f"{i}. {suggestion['japanese']} ({romaji})")
        else:
            print(f"{i}. {suggestion['japanese']}")
        meaning = suggestion.get("vietnamese_meaning")
        style = suggestion.get("style")
        nuance = suggestion.get("nuance")

        if meaning:
            print(f"   Ý nghĩa: {meaning}")
        if style:
            print(f"   Phong cách: {style}")
        if nuance:
            print(f"   Ghi chú: {nuance}")
        print()


if __name__ == "__main__":
    analysis = analyze_and_suggest_chat(HISTORY_FILE)
    print_analysis(analysis)