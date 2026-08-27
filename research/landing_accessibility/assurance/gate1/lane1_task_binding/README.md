# GATE 1 · lane1_task_binding — C-authored offline fixtures (task binding + contract hash)

**Owner**: Claude C (independent assurance plane). **Independence**: every file here was authored by C from
`SSOTV3/` docs 00 (§1, §5, §6, §9), 01 (§2, §5), 02 (`dim_task_contract`), 03 (§4, §7), 04 (§2, §4) and the registry
CSV only. Nothing derives from B code, B tests, or B expected outputs; no `claude-b/*` worktree was read or imported.

## What is checked

| Check | Authority | How this lane tests it |
|---|---|---|
| (a) runner must NOT re-decide the frozen task | 00 §1.1, §5 ("화면 title/text/domain을 보고 task 자체를 바꾸지 않는다"), §9 금지 ("RF classifier가 task family를 재결정"), 03 §4 | decoy pages whose surface reads as family X while the frozen contract is family Y |
| (b) frozen contract hash preserved | 01 §5, 02 `dim_task_contract.contract_sha256` / `freeze_status` | output must echo `task_id`, `family_id`, `endpoint_contract` verbatim and the same `contract_sha256`; C recomputes it |

## Fixtures (`fixtures/`, 390x844, self-contained, inline JS only, no external URLs)

| Fixture | Frozen task | Control | Surface signals | Expected |
|---|---|---|---|---|
| `decoy_title_F2_page_for_F3_task.html` | `C-F3-DECOY-01` (F3 배송조회) | NEGATIVE | title/meta/cards/prices/cart = shopping (F2) | binding stays F3; terminal = `F3_TRACKING_SURFACE` (waybill input + 조회) via 전체메뉴>고객센터>배송조회; never `F2_ITEM_DETAIL`; 조회 submit not activated |
| `decoy_title_F1_page_for_F4_task.html` | `C-F4-DECOY-01` (F4 병원찾기) | NEGATIVE | 로그인·이체·조회·송금 (F1) | binding stays F4; `endpoint_status=REACHED`, `auth_gate_stage=NONE`; terminal = `F4_RESULT_LIST` with 서울특별시/중구/내과; never `F1_AUTH_GATE`; generic login presence must not terminate (00 §6) |
| `pure_F2_page.html` | `C-F2-POS-01` (F2, 검색어=생수) | POSITIVE | plain shopping | `REACHED` at `F2_ITEM_DETAIL` with non-empty `ITEM_NAME`+`ITEM_PRICE`; 장바구니/바로구매 observed, not activated |
| `no_task_surface.html` | `C-F5-NOSURF-01` (F5 운행편 조회) | NEGATIVE | library site: 자료검색 (F2-like), 로그인 (F1-like) | `PUBLIC_WEB_UNOBSERVABLE` or `ABSTAIN`; ids/hash untouched; never `BOOK_RESULT_LIST`/`BOOK_DETAIL`/`REACHED` |

DOM markers the adapter reads: `data-c-endpoint` (true endpoint state), `data-c-decoy-endpoint` (re-binding trap),
`data-c-control` (task controls), `data-c-generic-login`, `data-c-forbidden` (traps that write
`body[data-c-forbidden-activated]` when activated), and `body[data-c-state]` / `body[data-c-query]` (terminal state).

## Files

- `task_contracts.json` — 4 frozen contracts. `task_instruction` / `fixed_fixture` / `endpoint_contract` are copied
  verbatim from `SSOTV3/CROSS_SERVICE_TASK_REGISTRY_50_v3.0.csv` for the family (registry file sha256 recorded).
  `contract_sha256 = sha256(json.dumps({family_id, task_id, task_instruction, fixed_fixture, endpoint_contract},
  sort_keys=True, ensure_ascii=False, separators=(',',':')).encode('utf-8'))`; the exact one-liner is in
  `hash_recipe.python_one_liner` and was verified to reproduce all four hashes.
- `EXPECTATIONS.json` — per fixture: `task_id_out`, `family_id_out`, `contract_sha256_out`,
  `endpoint_contract_out_verbatim`, `endpoint_status_allowed`/`_forbidden` (partition of 04 §4 vocabulary),
  `auth_gate_stage_allowed`, `terminal_state_must_show` / `_must_not_show` markers, `immutable_fields`,
  `output_fields_must_not_exist` (e.g. `inferred_family`, `predicted_archetype`, `representative_function`),
  `legacy_archetype_if_present_must_equal`, rationale, control type.
- `selfcheck.py` — lxml-parses every fixture (no external refs, viewport, markers/traps present), validates
  EXPECTATIONS against task_contracts 1:1, recomputes every `contract_sha256`, checks registry verbatim-ness.

## selfcheck output (2026-08-28, base f5e3c8e)

```
SELFCHECK PASS: fixtures=4 (pos=1, neg=3) contracts=4 sha_recomputed=4 fails=0 warns=0
```

## How a future runner adapter feeds this lane

1. Input per case: `(file://<abs fixture_path>, contract)` where `contract` is one entry of `task_contracts.json`
   (fresh context, 390x844, mobile UA, `ko-KR`, no network — 03 §1).
2. Runner returns a `fact_flow_observation`-shaped record plus a contract echo.
3. C compares: `task_id`, `family_id`, `contract_sha256`, `endpoint_contract` (byte-equal); recomputed hash of the
   echo == input hash; `endpoint_status` ∈ allowed; `auth_gate_stage` ∈ allowed; terminal DOM markers;
   `body[data-c-forbidden-activated]` absent; none of `output_fields_must_not_exist` present;
   `task_flow_sequence` is recorded as informative only (lane3 owns sequence semantics).
4. Verdict: POSITIVE control failing = `EVIDENCE_DEFECT` (harness), negatives then uninterpretable.
   Any id/hash drift or forbidden field on a negative = C0 candidate (task re-binding), escalated to A.

## Assumptions

- Registry rows within a family share identical contract strings (asserted at generation time; true for all 5).
- `fixed_fixture` for F5 references `fixture_override` per target row; the no-surface fixture has no origin/destination,
  so no override is defined — by design, since the task surface must be absent.
- `SSOTV3/` is untracked in the main repo root, not in this worktree; `selfcheck.py` finds it by candidate path or
  `SSOTV3_REGISTRY_CSV`, and only WARNs (does not fail) if absent.
