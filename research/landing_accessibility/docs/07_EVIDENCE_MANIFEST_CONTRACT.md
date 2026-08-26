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
| `verify_run(run_dir, require_files=True)` | manifest 를 기준선으로 로컬 파일의 존재·크기·해시를 대조 |
| `verify_run(run_dir, require_files=False)` | raw 가 없는 clone 용. **구조만 검증했다는 사실을 보고서 `mode` 에 남긴다** — 검사하지 않은 것을 통과로 세지 않는다 |
| `write_run_manifest()` | `(observation_id, relpath)` 정렬 + `sort_keys` 로 같은 입력이 같은 바이트를 내게 고정 |

`verify_run` 의 `status` 는 셋 중 하나다.

```
VERIFIED                              raw 를 전건 대조해 통과
MANIFEST_WELL_FORMED_FILES_NOT_CHECKED  manifest 는 정합하나 raw 를 보지 않았다
FAILED                                누락·크기 불일치·해시 불일치가 하나라도 있다
```

가운데 값이 `VERIFIED` 와 별개인 것이 핵심이다. 두 상태를 한 단어로 뭉개면
"파일이 없어서 검사를 못 한 것"이 "검사해서 통과한 것"으로 둔갑한다.

## 5. 이 계약이 하지 않는 것

- 이 모듈은 네트워크에 접근하지 않는다. E001 본수집과 무관하며, 수집을 승인하지도 않는다.
- manifest 는 원증거의 **대체물이 아니다.** raw 가 사라지면 내용 재검증은 불가능하고,
  가능해지는 것은 무결성·완결성 검증뿐이다. 이 한계를 확장 해석하지 않는다.
- Run 의 로컬 보존 책임은 여전히 실행자에게 있다. manifest 는 그 보존이 깨졌는지를 **알려줄** 뿐이다.
