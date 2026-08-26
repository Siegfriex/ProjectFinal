# 07 — 증거 Run manifest 계약

**상태** C012 exec 가 구조적 debt `gitignore-still-preexcludes-e001-evidence` 를 닫으며 작성.
**적용 시점** E001 본수집이 시작되기 **전**. 수집이 시작된 뒤에 만들면 이미 늦는다.

---

## 1. 문제

`.gitignore` 는 E001 증거를 수집하기 전부터 이렇게 제외하고 있었다.

```
evidence/*/dom/
evidence/*/ax/
evidence/*/screen/
evidence/*/probe/
```

한 줄도 수집하지 않은 시점에 **재검증 불가 구조를 이미 만들어 둔 것**이다.
Pilot 이 원증거 682MB 를 gitignore 해서 단일 머신에만 남긴 것과 정확히 같은 패턴이고,
그 자산은 지금 논리 백업으로만 남아 다른 clone 에서 재검증할 수 없다.

## 2. 왜 raw 는 그대로 제외하는가

DOM 스냅샷·AX 트리·풀페이지 스크린샷을 수백 MB 단위로 git 에 넣는 것은 다른 종류의 사고다.
clone 비용, 히스토리 영구 잔존, LFS 없는 저장소에서의 pack 팽창이 전부 실제 위험이다.
**제외 자체는 옳다. 제외를 감당 가능하게 만드는 조건이 없던 것이 틀렸다.**

## 3. 왜 manifest 는 추적하는가

`evidence/<run_id>/manifest.jsonl` 은 파일 하나당 한 줄이고 다음을 갖는다.

| 필드 | 의미 |
|---|---|
| `observation_id` | 어느 관측의 산출물인가 |
| `relpath` | Run 디렉터리 기준 상대경로 (절대경로·`..` 금지) |
| `sha256` | 접두사 없는 소문자 hex 64자 |
| `bytes` | 파일 크기 |

manifest 만 있으면, raw 바이트가 로컬에만 있어도 clone 을 받은 제3자가 다음을 확인할 수 있다.

- Run 에 관측이 몇 건 있었는가 — 사후에 관측을 **추가하거나 삭제**하면 manifest 가 어긋난다
- 각 관측이 어떤 산출물을 몇 바이트로 남겼는가
- 자기 손에 raw 가 있다면 그 바이트가 선언된 해시와 같은가

**재현은 못 해도 위조는 잡힌다.** 제외의 대가로 잃는 것을 이 지점까지 좁히는 것이 계약의 목적이다.

## 4. 계약 — 문서가 아니라 코드가 강제한다

`src/landing_accessibility/evidence_manifest.py`

| 함수 | 계약 |
|---|---|
| `load_run_manifest(run_dir)` | manifest 부재 → `MissingRunManifestError`. **manifest 없는 Run 은 유효하지 않다.** |
| | 필수 필드 누락·sha256 형식 위반·relpath 절대경로·`(observation_id, relpath)` 중복·빈 파일 → `MalformedRunManifestError` |
| `verify_run(run_dir, require_files=True)` | manifest 를 기준선으로 로컬 파일의 존재·크기·해시를 대조. 파일 부재를 **실패로 센다** |
| `verify_run(run_dir, require_files=False)` | raw 가 없는 clone 용. 파일 부재를 실패로 세지 **않는다**. 그것이 이 플래그가 정하는 전부다 |
| `resolve_entry_path(run_dir, relpath)` | relpath 를 실제 경로로 해석하며 symlink 탈출을 차단 → `SymlinkEscapeError` |
| `write_run_manifest()` | `(observation_id, relpath)` 정렬 + `sort_keys` 로 같은 입력이 같은 바이트를 내게 고정 |

`verify_run` 의 `status` 는 셋 중 하나다.

```
VERIFIED                              raw 를 전건 대조해 통과
MANIFEST_WELL_FORMED_FILES_NOT_CHECKED  manifest 는 정합하나 raw 를 전건 보지는 않았다
FAILED                                누락·크기 불일치·해시 불일치·symlink 탈출이 하나라도 있다
```

가운데 값이 `VERIFIED` 와 별개인 것이 핵심이다. 두 상태를 한 단어로 뭉개면
"파일이 없어서 검사를 못 한 것"이 "검사해서 통과한 것"으로 둔갑한다.

### 4-1. `mode` 는 요청이 아니라 측정이다 `[V2-C008 시정]`

닫는 결함: `verify-run-mislabels-mode-and-symlink-bypasses-relpath-guard` (v1 승계, 전반부)

옛 구현은 `mode` 를 `require_files` 플래그에서 **그대로 찍었다.**

```python
"mode": "FULL_BYTE_VERIFICATION" if require_files else "STRUCTURE_ONLY_RAW_ABSENT",
```

그래서 raw 를 전부 가진 clone 이 `require_files=False` 로 부르면, 전건을 해시해 놓고도
보고서에는 `STRUCTURE_ONLY_RAW_ABSENT` 와 `MANIFEST_WELL_FORMED_FILES_NOT_CHECKED` 가
남았다. 라벨이 **의도**를 말하고 **사실**을 말하지 않으면 그것은 검증 기록이 아니다.
반대 방향도 같다 — 일부 파일만 있는 clone 도 같은 라벨을 받아, 보고서만 읽는 제3자는
무엇이 검사됐는지 알 수 없었다. (그 오라벨을 `tests/test_c012_review_and_grouping.py` 가
`assert partial["mode"] == "STRUCTURE_ONLY_RAW_ABSENT"` 로 **사실처럼 고정**하고 있었다.)

이제 `mode` 는 `files_checked` 에서 유도된다.

| `files_checked` | `mode` |
|---|---|
| `== entries` | `FULL_BYTE_VERIFICATION` |
| `0 < n < entries` | `PARTIAL_BYTE_VERIFICATION` |
| `== 0` | `STRUCTURE_ONLY_RAW_ABSENT` |

`status` 어휘 3값은 `A2 §4.1` 이 이미 묶어 뒀으므로 바꾸지 않는다. 다만 그 유도가
`require_files` 가 아니라 `mode` 를 본다 — `FULL_BYTE_VERIFICATION` 일 때만 `VERIFIED` 다.
요청 플래그 자체도 `require_files` 로 보고서에 남겨 정책과 사실을 둘 다 보이게 한다.

### 4-2. relpath 규칙은 문자열 검사였다 `[V2-C008 시정]`

닫는 결함: `verify-run-mislabels-mode-and-symlink-bypasses-relpath-guard` (v1 승계, 후반부)

`load_run_manifest` 의 relpath 검사(절대경로 금지 · `..` 금지)는 **문자열**만 본다.
Run 디렉터리 안에서 `dom` 을 `/etc` 로 링크해 두면 `dom/passwd` 는 그 규칙을
한 글자도 위반하지 않고, 옛 `verify_run` 은 `run_dir / relpath` 를 그대로 열어
**Run 밖 바이트를 해시하고 `VERIFIED` 를 돌려줬다.**

`resolve_entry_path()` 가 두 겹으로 막는다.

1. 경로 성분 하나라도 symlink 면 거부한다. `realpath` 결과가 Run 안이어도 거부한다 —
   "지금은 안을 가리키는 링크" 는 다음 검증 전에 바깥을 가리키도록 바뀔 수 있고, 그때
   `realpath` 검사만으로는 통과한다. evidence 층에 링크가 있을 이유가 없다.
2. `os.path.realpath` 로 푼 최종 경로가 Run 실경로 안인지 확인한다 (부모 교체 경합 대비).

탈출로 판정된 항목은 **해시하지 않는다.** 해시하면 Run 밖 바이트가 증거로 남는다.
보고서 `symlink_escape` 에 기록되고 `status` 는 `FAILED` 다.
LANE C 가 P-C **쓰기** 경로에 만든 `engine/evidence.py::_assert_no_symlink_escape` 와
같은 정책이며, 이 모듈은 그 정책이 없던 **읽기·검증** 경로다.

## 5. 이 계약이 하지 않는 것

- 이 모듈은 네트워크에 접근하지 않는다. E001 본수집과 무관하며, 수집을 승인하지도 않는다.
- manifest 는 원증거의 **대체물이 아니다.** raw 가 사라지면 내용 재검증은 불가능하고,
  가능해지는 것은 무결성·완결성 검증뿐이다. 이 한계를 확장 해석하지 않는다.
- Run 의 로컬 보존 책임은 여전히 실행자에게 있다. manifest 는 그 보존이 깨졌는지를 **알려줄** 뿐이다.
