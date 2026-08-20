"""ProjectFinal 환경 종합 검증 — 주요 라이브러리 임포트와 GPU 가용성을 확인한다."""

from __future__ import annotations

import importlib
import sys

GROUPS: dict[str, list[str]] = {
    "코어": ["numpy", "pandas", "scipy", "sklearn", "statsmodels", "polars", "duckdb", "pyarrow"],
    "딥러닝": [
        "torch",
        "torchvision",
        "torchaudio",
        "transformers",
        "sentence_transformers",
        "datasets",
        "accelerate",
        "tensorflow",
        "keras",
        "xgboost",
        "lightgbm",
        "catboost",
    ],
    "비전/OCR": [
        "cv2",
        "PIL",
        "skimage",
        "albumentations",
        "ultralytics",
        "easyocr",
        "pytesseract",
        "fitz",
        "pdfplumber",
    ],
    "NLP": ["nltk", "konlpy", "kiwipiepy", "spacy", "gensim", "tiktoken"],
    "시각화": ["matplotlib", "seaborn", "plotly", "altair", "bokeh", "graphviz", "pydot"],
    "LLM/RAG": [
        "langchain",
        "llama_index.core",
        "chromadb",
        "faiss",
        "qdrant_client",
        "litellm",
        "openai",
        "anthropic",
    ],
    "웹/앱": ["fastapi", "uvicorn", "flask", "streamlit", "gradio", "pydantic"],
    "자동화": ["playwright", "selenium", "bs4", "httpx", "lxml", "trafilatura"],
    "오디오": ["librosa", "soundfile", "whisper"],
    "DB/스토리지": ["redis", "psycopg", "pymysql", "boto3", "minio", "sqlalchemy"],
    "도구": ["pytest", "ruff", "mypy", "black", "rich", "typer", "loguru", "jupyterlab"],
}


def main() -> int:
    failures: list[tuple[str, str]] = []
    for group, mods in GROUPS.items():
        line: list[str] = []
        for mod in mods:
            try:
                m = importlib.import_module(mod)
                ver = getattr(m, "__version__", "")
                line.append(f"{mod}{'=' + ver if ver else ''}")
            except Exception as exc:
                line.append(f"✗{mod}")
                failures.append((mod, f"{type(exc).__name__}: {exc}"))
        print(f"[{group}] " + "  ".join(line))

    print()
    try:
        import torch

        print(
            f"torch {torch.__version__} | CUDA {torch.version.cuda} | 사용 가능 {torch.cuda.is_available()}"
        )
        if torch.cuda.is_available():
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
            print(f"  아키텍처: {', '.join(torch.cuda.get_arch_list())}")
            x = torch.randn(2048, 2048, device="cuda")
            print(f"  행렬곱 검증: {(x @ x).sum().item():.2f}")
    except Exception as exc:
        print(f"torch 검증 실패: {exc}")
        failures.append(("torch-cuda", str(exc)))

    if failures:
        print(f"\n실패 {len(failures)}건:")
        for mod, err in failures:
            print(f"  - {mod}: {err[:120]}")
        return 1
    print("\n전체 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
