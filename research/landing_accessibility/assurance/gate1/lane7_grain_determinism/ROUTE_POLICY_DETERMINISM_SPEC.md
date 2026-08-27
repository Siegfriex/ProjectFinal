# ROUTE_POLICY_DETERMINISM_SPEC — runner-agnostic test spec + policy-document checklist (GATE 1 must_include 4)

**Owner**: Claude C. **Authority**: SSOTV3 `03` §4 (candidate binding: ranking may assist, may not change the task label),
`03` §5 (Scout → Freeze → Replay: "최소 허용 path", "deterministic하게 재생", `REPLAY_BROKEN` never silently replaced by
free exploration), `04` §2-§5 (token set, task vs experienced flow, derived counts), `05` §2E (flow topology is analysed
from sequence signatures — a non-deterministic route policy makes the signature a property of the run, not the service).
The "control/v3 Δ6-d" text was not present in C's permitted read set (only the Δ6 E-integration finding exists in
`bus_mirror_c`); this spec is therefore pre-registered against SSOTV3 and C's FREEZE ACK item (4) only.

## 1. Test (what `determinism_check.py` asserts)

Given a command template `CMD` with placeholders `{fixture}` `{out}`, a fixture `F`, and `N ≥ 3`:

1. Run `CMD` N times on the same `F`; each run writes a sequence JSON to `{out}`.
2. From each JSON extract `task_flow_sequence`, `experienced_flow_sequence`, and the ordered `control_selector`
   list of `steps[*]` (or `selected_control_selectors`). Serialise each canonically (UTF-8, sorted keys, no spaces).
3. **PASS iff** the three serialisations are byte-identical across all N runs. Raw-file identity is *not* required
   (timestamps/run ids may differ) and is printed for information only.
4. Record `sha256(policy document)` next to the verdict so a later policy edit invalidates the GATE record.
5. Exit codes: 0 PASS, 1 FAIL (non-determinism), 2 runner/usage error — a runner that fails to write the JSON is
   neither PASS nor FAIL (fail-closed, "no result ≠ pass").

Controls: `fake_runner_det.py` (must PASS) and `fake_runner_rand.py` (must FAIL) are run before any real runner; a
check that cannot distinguish them is not admissible.

For the real B runner the same command is issued on the frozen 12/50 fixtures with `N=3`; a FAIL on any fixture blocks
GATE 1 regardless of whether the replayed endpoint was reached.

## 2. Checklist — what a deterministic route-selection policy document must state

| # | Item | Must state |
|---|---|---|
| RP-01 | Candidate enumeration | the exact source set (button/link/tab/menuitem/input/searchbox/card, `03` §4) and the DOM/AX snapshot it is computed from (state id) |
| RP-02 | Candidate ranking rule | a total pre-order over candidates written as an ordered list of keys (e.g. exact-name match > accessible-name match > href match > geometry), each key's normalisation (NFKC, casefold, whitespace) |
| RP-03 | Tie-break | a *total* order after all ranking keys: document order, then selector string — never "first found", never hash/set iteration order |
| RP-04 | Shortest-path definition | what is minimised (`activation_depth` per `04` §5, excluding scroll/dismiss/typing), and what happens on equal length (fewest menu reveals → RP-03) |
| RP-05 | Stop conditions | endpoint predicate (`endpoint_contract`), `AUTH_GATE`, `BLOCKED`, `ABSTAIN` triggers, max depth, max wall-clock — all as fixed constants |
| RP-06 | Random seed = none | the policy uses no RNG; any library with internal randomness (embedding search, LLM ranking) is either disabled or pinned to a seed *and* declared as `selection_basis` |
| RP-07 | Dismissal policy | which obstructions are dismissed (only `dismiss_required_for_task = True`), in which order (z-index desc, document order), "one attempt per interrupt", and that dismissal never counts in `task_flow_sequence` |
| RP-08 | Scroll policy | fixed scroll steps (px) and maximum; scroll is exposure, not an action |
| RP-09 | Time/network independence | waits are bounded by fixed stabilisation predicates, not by wall-clock at decision points; decisions never read `Date.now()`-like values |
| RP-10 | Replay contract | replay consumes the frozen manifest only; deviation ⇒ `REPLAY_BROKEN`, never re-scout (`03` §5) |
| RP-11 | Policy identity | version string + sha256 of the policy text embedded in every sequence JSON (`policy_sha256`) |
| RP-12 | Determinism evidence | N=3 same-fixture byte-identical result for every frozen fixture, produced by `determinism_check.py` or an equivalent C-run check |

A policy document missing any RP item is **not** deterministic by construction, even if a run happened to pass.
