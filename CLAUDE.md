# ProjectFinal

**이 저장소가 모든 작업의 메인 코드베이스다.** 워크트리, 서브에이전트, 워크플로 에이전트를
포함한 모든 에이전트는 `/home/sieg/projects-wsl/ProjectFinal`을 루트로 잡고 작업한다.
상위 형제 디렉터리(`../KOEN_*`, `../Tokenization_*`, `../SBS_dataScience` …)는 **읽기 참조 전용**이며,
그쪽 파일을 수정하지 않는다.

- 원격: `https://github.com/Siegfriex/ProjectFinal.git` (origin/main)

## 환경 활성화

```bash
source scripts/activate.sh     # Python + Java + Node + 브라우저 경로 일괄 설정
```

에이전트 세션은 `.claude/settings.json`의 `env`로 동일한 경로가 자동 주입되므로
별도 활성화 없이 `python`, `mmdc`, `mvn`, `gradle`이 바로 잡힌다.

## 런타임 스택

| 영역 | 내용 |
|---|---|
| GPU | NVIDIA RTX 5070 Ti Laptop (12GB, **sm_120**), 드라이버 CUDA 13.2 |
| Python | 3.12.3 · 통합 환경 `.venv` (uv 관리, hardlink) |
| PyTorch | `2.13.0+cu130` / torchvision `0.28.0+cu130` / torchaudio `2.11.0+cu130` |
| Node | v20.20.1 · npm 10.8.2 · pnpm · yarn · tsx · TypeScript |
| Java | Temurin **21.0.4** (17.0.12 병행) · Maven 3.9.16 · Gradle 9.7.0 · Spring Boot CLI 4.0.3 |
| 다이어그램 | `mmdc` (mermaid-cli 11) → Chrome 백엔드, 설정 `.config/puppeteer.json` |
| 브라우저 자동화 | Playwright(캐시 재사용) · Selenium · google-chrome |
| 컨테이너 | Docker 29.1.3 |

sm_120 대응은 **cu130 휠에서만** 동작한다. torch를 재설치할 때는 반드시
`--index-url https://download.pytorch.org/whl/cu130` 을 붙인다.

## 파이썬 환경 규약

- 패키지 설치는 **uv**로만: `uv pip install --python .venv/bin/python <pkg>`
- `pip install`을 전역으로 실행하지 않는다.
- 재현: `scripts/bootstrap_venv.sh` (베이스 = `requirements/base-koen.freeze.txt`, 추가 = `requirements/extras.txt`)

### 상위 프로젝트 환경 재사용

`env/` 아래에 상위 venv들이 심링크로 연결돼 있다 (git 추적 제외).

| 심링크 | 원본 | 특징 |
|---|---|---|
| `env/koen` | `../Tokenization_KOEN/.venv` | torch cu130, spacy/konlpy/kiwipiepy, xgboost |
| `env/sbs-ds` | `../SBS_dataScience/.venv` | opencv, tensorflow, deepface, playwright |
| `env/hongik` | `../hongikUniv.-26_1/.venv` | 강의용 데이터 분석 스택 |
| `env/mbn` | `../mbN_GUIDE_PY/.venv` | torch cu130 + opencv-headless |
| `env/ai-env` | `~/ai-env` | 경량 추론 환경 |
| `env/dsja`, `env/miriart` | 각 프로젝트 | 소형 전용 환경 |

특정 환경으로 스크립트를 돌릴 때: `env/sbs-ds/bin/python script.py`
Jupyter에서 고르려면: `scripts/register_kernels.sh` 실행 후 커널 선택.

## 디렉터리

```
src/          라이브러리 코드 (PYTHONPATH에 등록됨)
tests/        pytest
notebooks/    주피터
scripts/      운영 스크립트
data/         raw → interim → processed (git 추적 제외)
artifacts/    산출물·로그 (git 추적 제외)
requirements/ 의존성 명세
env/          상위 venv 심링크 (로컬 전용)
```

## 품질 게이트

```bash
ruff check . && ruff format --check .
mypy src
pytest -q
```

## 다이어그램

```bash
mmdc -i docs/x.mmd -o artifacts/x.svg -p .config/puppeteer.json
```

Markdown 안의 ```mermaid``` 블록은 그대로 두고, 렌더 산출물만 `artifacts/`에 둔다.

## 워크트리

워크트리는 `.venv`/`env`/`node_modules`를 git으로 가져오지 않는다. 새 워크트리를 만든 직후
반드시 연결한다:

```bash
scripts/setup_worktree.sh /path/to/worktree
```

메인의 환경을 심링크로 공유하므로 재설치가 필요 없고, 12GB를 중복으로 쓰지 않는다.

## 알려진 제약

- `sudo`가 패스워드를 요구해 **apt 설치는 사용자 개입 없이 불가**. 필요한 경우 사용자에게
  `! sudo apt install ...` 실행을 요청한다.
- `dot`(graphviz 바이너리)가 없다. 파이썬 `graphviz`/`pydot` 패키지는 설치돼 있으나 렌더는 실패한다.
  → 다이어그램은 **mermaid(`mmdc`)를 우선 사용**한다.
- `ffmpeg`, `pandoc`은 apt 없이 파이썬 패키지로 확보돼 있다:
  - ffmpeg → `imageio_ffmpeg.get_ffmpeg_exe()`
  - pandoc 3.9 → `pypandoc` (번들 바이너리)
- 의존성 상한은 `requirements/constraints.txt`에 모여 있다. **설치·업그레이드 시 항상**
  `-c requirements/constraints.txt`를 붙인다. 빼면 tokenizers/jiter/fsspec/pandas가
  올라가면서 `transformers`·`instructor`·`mlflow`가 깨진다.
- `env/dsja`, `env/miriart`, `env/ai-env`는 ipykernel이 없어 Jupyter 커널로 등록되지 않는다.
  상위 환경은 수정하지 않는 원칙이라 그대로 둔다 — 필요하면 `.venv`에서 작업한다.

## 검증

```bash
python scripts/verify_env.py     # 61개 라이브러리 임포트 + GPU 행렬곱
uv pip check --python .venv/bin/python
pytest -q
```
