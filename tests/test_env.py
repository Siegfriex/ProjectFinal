"""환경 스모크 테스트."""

import importlib

import pytest


@pytest.mark.parametrize(
    "mod", ["numpy", "pandas", "sklearn", "matplotlib", "cv2", "torch", "polars", "duckdb"]
)
def test_import(mod: str) -> None:
    assert importlib.import_module(mod) is not None


@pytest.mark.gpu
def test_cuda_available() -> None:
    torch = importlib.import_module("torch")
    assert torch.cuda.is_available(), "CUDA를 사용할 수 없다"
    assert "sm_120" in torch.cuda.get_arch_list(), "sm_120 커널이 없는 휠이다"
