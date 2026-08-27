"""Lane L — Label / Accessible Name axis harness (Claude D, V3 sandbox).

Scope (contract): implement ONLY what SSOTV3 04_FLOW_CODEBOOK_v3.0.md has already
frozen, for the Label / Accessible Name axis:

  visible_label_text, accessible_name, accessible_name_source,
  label_relation, entry_label_modality

plus two counterexample detectors:

  CE-1  same accessible_name, different visible_label_text
  CE-2  same visible_label_text, different entry_control_type

Hard rules honoured here
------------------------
* `visible_label_text` and `accessible_name` are NEVER merged, defaulted into one
  another, or back-filled from one another (SSOT 00 §8).
* `label_relation` = Unicode normalize + whitespace normalize -> **exact** compare.
  Semantic equivalence is flagged ONLY through a pre-frozen synonym map.
  Embedding / fuzzy / edit-distance merging is NOT implemented and MUST NOT be added
  here (04 §5).
* The synonym map ships EMPTY. Filling it is A's authority, not D's. Until A supplies
  an authored map, `SEMANTIC_EQUIV` is unreachable on real data by construction.
* No thresholds, no similarity cutoffs, no composite scores anywhere in this file.
* `entry_control_type` is an INPUT field only. This module does not classify control
  type and does not read any Lane S artifact.
* Missing (`None`, never observed) and empty (`""`, observed and empty) are distinct
  states end to end. Empty is NOT collapsed into `NONE`.
* Any HTML that is read goes through `research_d/tools/html_decode.parse_html`
  (D-DEF-01: passing raw bytes to lxml produces mojibake).

Ambiguity policy
----------------
Where the codebook fixes an enum but not the procedure that yields it, this module
computes a PRIMARY value under an explicitly named reading, ALSO computes the
competing reading(s) as variants, and reports divergence instead of hiding it.
Every such point is listed in `AMBIGUOUS_DEFINITIONS` and needs an A ruling.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

RD = Path(__file__).resolve().parents[2]
if str(RD / "tools") not in sys.path:
    sys.path.insert(0, str(RD / "tools"))

from html_decode import parse_html  # noqa: E402  (D-DEF-01 mandated decoder)

SSOT_DIR = Path("/home/sieg/projects-wsl/ProjectFinal/SSOTV3")
CODEBOOK = SSOT_DIR / "04_FLOW_CODEBOOK_v3.0.md"
OUT_DIR = RD / "results" / "harness" / "lane_l"

# --------------------------------------------------------------------------------------
# Frozen enums (verbatim from 04 §4)
# --------------------------------------------------------------------------------------
ACCESSIBLE_NAME_SOURCE = (
    "VISIBLE_TEXT", "ARIA_LABEL", "ARIA_LABELLEDBY", "LABEL",
    "ALT", "TITLE", "VALUE", "MIXED", "NONE",
)
LABEL_RELATION = (
    "MATCH", "SEMANTIC_EQUIV", "DIFFERENT", "VISIBLE_ONLY", "AX_ONLY", "NONE",
)
ENTRY_LABEL_MODALITY = (
    "EXPLICIT_TEXT", "ICON_TEXT", "ICON_ONLY_AX_NAMED",
    "ICON_ONLY_UNNAMED", "HIDDEN_UNTIL_REVEAL",
)

# Name-source candidate keys the attributor understands. VISIBLE_TEXT is included so a
# name that came from rendered content is attributable, but the candidate value is still
# stored separately from `visible_label_text` -- they are never unified.
NAME_SOURCE_KEYS = (
    "ARIA_LABELLEDBY", "ARIA_LABEL", "LABEL", "ALT", "VALUE", "VISIBLE_TEXT", "TITLE",
)
# Tie-break order only. Used ONLY when two or more candidates carry the *same* value as
# the computed name, so attribution by value alone cannot separate them.
# Source: W3C accname 1.2 precedence. The codebook does not fix this -> AMB-L-04.
ACCNAME_PRECEDENCE = (
    "ARIA_LABELLEDBY", "ARIA_LABEL", "LABEL", "ALT", "VALUE", "VISIBLE_TEXT", "TITLE",
)

ZERO_WIDTH_CHARS = "\u200b\u200c\u200d\u2060\ufeff"  # ZWSP ZWNJ ZWJ WJ BOM

# --------------------------------------------------------------------------------------
# Synonym map hook -- INTENTIONALLY EMPTY. A owns its contents.
# --------------------------------------------------------------------------------------
SYNONYM_MAP_AUTHORITY = "A"
SYNONYM_MAP: dict[str, str] = {}
"""Maps a normalized surface form -> a canonical concept id.

EMPTY BY CONTRACT. D (this lane) must not populate it. Two labels are marked
SEMANTIC_EQUIV iff both normalized forms are present in the map AND map to the same
concept id. There is no similarity computation, no fallback, and no partial match.

To install a real map, A writes a JSON file:
    {"authority": "A", "version": "...", "map": {"<normalized form>": "<concept id>"}}
and it is loaded with `load_synonym_map(path)`, which refuses any file whose
`authority` is not "A".
"""


def load_synonym_map(path: Path) -> dict[str, str]:
    """Install an A-authored synonym map. Refuses non-A authored files."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("authority") != SYNONYM_MAP_AUTHORITY:
        raise PermissionError(
            f"synonym map authority must be {SYNONYM_MAP_AUTHORITY!r}, got {doc.get('authority')!r}"
        )
    SYNONYM_MAP.clear()
    SYNONYM_MAP.update({str(k): str(v) for k, v in doc.get("map", {}).items()})
    return dict(SYNONYM_MAP)


# --------------------------------------------------------------------------------------
# Mutation hooks (for mutation testing only; inert when _MUT is empty)
# --------------------------------------------------------------------------------------
_MUT: set[str] = set()


@contextmanager
def mutation(*names: str):
    """Temporarily corrupt the calculator to check the fixtures actually bite."""
    prev = set(_MUT)
    _MUT.update(names)
    try:
        yield
    finally:
        _MUT.clear()
        _MUT.update(prev)


def _m(name: str) -> bool:
    return name in _MUT


# --------------------------------------------------------------------------------------
# Normalization
# --------------------------------------------------------------------------------------
def normalize_text(
    s: str | None,
    *,
    form: str = "NFC",
    strip_zero_width: bool = False,
    casefold: bool = False,
) -> str | None:
    """04 §5: 'Unicode normalize + whitespace normalize 후 exact'.

    PRIMARY reading = NFC (canonical only), zero-width preserved, case preserved.
    See AMB-L-01/02/03 for the readings this deliberately does not take.
    Whitespace normalization = strip + collapse every run of Unicode whitespace
    (which includes NBSP U+00A0 and ideographic space U+3000) to a single U+0020.
    """
    if s is None:
        return None
    if _m("M4_NO_UNICODE_NORMALIZE"):
        t = s
    else:
        t = unicodedata.normalize("NFKC" if (_m("M2_NFKC_PRIMARY") or form == "NFKC") else form, s)
    if strip_zero_width or _m("M7_STRIP_ZERO_WIDTH"):
        t = t.translate({ord(c): None for c in ZERO_WIDTH_CHARS})
    if not _m("M1_NO_WHITESPACE_COLLAPSE"):
        t = " ".join(t.split())
    if casefold or _m("M3_CASEFOLD_PRIMARY"):
        t = t.casefold()
    return t


VARIANT_READINGS: dict[str, dict[str, Any]] = {
    "primary": {"form": "NFC", "strip_zero_width": False, "casefold": False},
    "nfkc": {"form": "NFKC", "strip_zero_width": False, "casefold": False},
    "zero_width_stripped": {"form": "NFC", "strip_zero_width": True, "casefold": False},
    "casefolded": {"form": "NFC", "strip_zero_width": False, "casefold": True},
}

TEXT_STATES = ("MISSING", "EMPTY", "PRESENT")


def text_state(s: str | None, **norm_kw: Any) -> str:
    """MISSING (never observed / None) vs EMPTY (observed, normalizes to '') vs PRESENT.

    These three are kept apart everywhere. EMPTY is never rewritten as MISSING and
    neither is silently turned into the `NONE` enum member.
    """
    if s is None:
        return "MISSING"
    if _m("M5_EMPTY_IS_MISSING") and normalize_text(s, **norm_kw) == "":
        return "MISSING"
    return "EMPTY" if normalize_text(s, **norm_kw) == "" else "PRESENT"


# --------------------------------------------------------------------------------------
# Observation record
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class LabelObservation:
    """One task-entry control observation, Label/AX axis only.

    `entry_control_type` is carried through untouched for CE-2. This module neither
    derives nor validates it; the taxonomy belongs to another lane.
    """
    observation_id: str
    visible_label_text: str | None = None          # rendered text, or None if unobserved
    accessible_name: str | None = None             # AX computed name, or None if unobserved
    name_source_candidates: dict[str, str | None] | None = None
    accessible_name_source_observed: str | None = None  # collector-asserted, wins if given
    has_icon: bool | None = None
    requires_reveal: bool | None = None
    entry_control_type: str | None = None          # INPUT ONLY
    notes: str | None = None


# --------------------------------------------------------------------------------------
# label_relation
# --------------------------------------------------------------------------------------
def label_relation(
    visible_label_text: str | None,
    accessible_name: str | None,
    *,
    synonym_map: dict[str, str] | None = None,
    **norm_kw: Any,
) -> dict[str, Any]:
    smap = SYNONYM_MAP if synonym_map is None else synonym_map
    if _m("M12_AX_FALLBACK_TO_VISIBLE") and accessible_name is None:
        accessible_name = visible_label_text  # forbidden merge (SSOT 00 §8)
    v_state = text_state(visible_label_text, **norm_kw)
    a_state = text_state(accessible_name, **norm_kw)
    v = normalize_text(visible_label_text, **norm_kw)
    a = normalize_text(accessible_name, **norm_kw)

    out: dict[str, Any] = {
        "visible_state": v_state,
        "ax_state": a_state,
        "visible_normalized": v,
        "ax_normalized": a,
        "label_relation": None,
        "undeterminable_reason": None,
    }

    # A side that was never observed cannot support any of the six enum members: the
    # codebook has no value meaning "not observed", so we emit None + a reason rather
    # than manufacture one.
    if v_state == "MISSING" or a_state == "MISSING":
        out["undeterminable_reason"] = {
            ("MISSING", "MISSING"): "BOTH_UNOBSERVED",
            ("MISSING", "EMPTY"): "VISIBLE_UNOBSERVED",
            ("MISSING", "PRESENT"): "VISIBLE_UNOBSERVED",
            ("EMPTY", "MISSING"): "AX_UNOBSERVED",
            ("PRESENT", "MISSING"): "AX_UNOBSERVED",
        }[(v_state, a_state)]
        return out

    if v_state == "EMPTY" and a_state == "EMPTY":
        out["label_relation"] = "NONE"
        return out
    if v_state == "PRESENT" and a_state == "EMPTY":
        out["label_relation"] = "VISIBLE_ONLY"
        return out
    if v_state == "EMPTY" and a_state == "PRESENT":
        out["label_relation"] = "VISIBLE_ONLY" if _m("M11_ONLY_SIDE_COLLAPSE") else "AX_ONLY"
        return out

    if v == a:
        out["label_relation"] = "MATCH"
        return out
    if v in smap and a in smap and smap[v] == smap[a]:
        out["label_relation"] = "SEMANTIC_EQUIV"
        out["synonym_concept_id"] = smap[v]
        return out
    out["label_relation"] = "DIFFERENT"
    return out


def label_relation_all_readings(
    visible_label_text: str | None,
    accessible_name: str | None,
    *,
    synonym_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Primary + every competing normalization reading, with divergence flagged."""
    readings = {
        name: label_relation(visible_label_text, accessible_name,
                             synonym_map=synonym_map, **kw)
        for name, kw in VARIANT_READINGS.items()
    }
    primary = readings["primary"]
    diverging = sorted(
        n for n, r in readings.items()
        if n != "primary" and (r["label_relation"], r["undeterminable_reason"])
        != (primary["label_relation"], primary["undeterminable_reason"])
    )
    return {
        **primary,
        "readings": {n: {"label_relation": r["label_relation"],
                         "undeterminable_reason": r["undeterminable_reason"]}
                     for n, r in readings.items()},
        "normalization_sensitive": bool(diverging),
        "diverging_readings": diverging,
    }


# --------------------------------------------------------------------------------------
# accessible_name_source
# --------------------------------------------------------------------------------------
def accessible_name_source(
    accessible_name: str | None,
    name_source_candidates: dict[str, str | None] | None,
    *,
    observed: str | None = None,
    **norm_kw: Any,
) -> dict[str, Any]:
    """Attribute the AX name to the DOM/ARIA source that produced it.

    Evidence-first: attribution is by exact normalized value match against the candidate
    values the collector recorded. Precedence is a TIE-BREAK ONLY, never a substitute
    for evidence. When the name matches nothing, the value is left None with a reason
    rather than forced into an enum member.
    """
    out: dict[str, Any] = {
        "accessible_name_source": None,
        "unresolved_reason": None,
        "matched_sources": [],
        "ambiguous": False,
        "derivation": None,
    }
    if observed is not None:
        if observed not in ACCESSIBLE_NAME_SOURCE:
            out["unresolved_reason"] = f"INVALID_OBSERVED_VALUE:{observed}"
            return out
        out["accessible_name_source"] = observed
        out["derivation"] = "COLLECTOR_ASSERTED"
        return out

    a_state = text_state(accessible_name, **norm_kw)
    if a_state == "MISSING":
        out["unresolved_reason"] = "AX_NAME_UNOBSERVED"
        return out

    cands = {k: v for k, v in (name_source_candidates or {}).items()
             if k in NAME_SOURCE_KEYS and text_state(v, **norm_kw) == "PRESENT"}

    if a_state == "EMPTY":
        if not cands:
            out["accessible_name_source"] = "NONE"
            out["derivation"] = "EMPTY_NAME_NO_CANDIDATE"
            return out
        # Observed-empty name while naming candidates exist: contradictory evidence.
        out["unresolved_reason"] = "EMPTY_NAME_WITH_CANDIDATES"
        out["matched_sources"] = sorted(cands)
        return out

    if name_source_candidates is None:
        out["unresolved_reason"] = "CANDIDATES_UNOBSERVED"
        return out

    a = normalize_text(accessible_name, **norm_kw)
    matched = [k for k, v in cands.items() if normalize_text(v, **norm_kw) == a]
    if len(matched) == 1:
        out["accessible_name_source"] = matched[0]
        out["matched_sources"] = matched
        out["derivation"] = "UNIQUE_VALUE_MATCH"
        return out
    if len(matched) > 1:
        order = list(ACCNAME_PRECEDENCE)
        if _m("M8_REVERSE_PRECEDENCE"):
            order = order[::-1]
        winner = sorted(matched, key=order.index)[0]
        out["accessible_name_source"] = winner
        out["matched_sources"] = sorted(matched)
        out["ambiguous"] = True
        out["derivation"] = "PRECEDENCE_TIEBREAK"
        return out

    # MIXED: the name is a concatenation of two or more candidate values.
    if not _m("M6_NO_MIXED") and len(cands) >= 2:
        for size in (2, 3):
            for combo in itertools.permutations(sorted(cands), size):
                joined = " ".join(normalize_text(cands[k], **norm_kw) or "" for k in combo)
                if normalize_text(joined, **norm_kw) == a:
                    out["accessible_name_source"] = "MIXED"
                    out["matched_sources"] = list(combo)
                    out["derivation"] = "CONCATENATION_MATCH"
                    return out

    out["unresolved_reason"] = "NAME_NOT_ATTRIBUTABLE"
    out["matched_sources"] = []
    return out


# --------------------------------------------------------------------------------------
# entry_label_modality
# --------------------------------------------------------------------------------------
def entry_label_modality(
    visible_label_text: str | None,
    accessible_name: str | None,
    *,
    has_icon: bool | None,
    requires_reveal: bool | None,
    **norm_kw: Any,
) -> dict[str, Any]:
    """EXPLICIT_TEXT / ICON_TEXT / ICON_ONLY_AX_NAMED / ICON_ONLY_UNNAMED / HIDDEN_UNTIL_REVEAL.

    ICON_ONLY_AX_NAMED vs ICON_ONLY_UNNAMED is decided *only* by the AX name state, per
    SSOT 00 §8. An observed-empty AX name yields UNNAMED; an unobserved AX name yields
    no value at all (the distinction the contract forbids collapsing).
    """
    if _m("M12_AX_FALLBACK_TO_VISIBLE") and accessible_name is None:
        accessible_name = visible_label_text  # forbidden merge (SSOT 00 §8)
    out: dict[str, Any] = {
        "entry_label_modality": None,
        "undeterminable_reason": None,
        "inputs": {
            "visible_state": text_state(visible_label_text, **norm_kw),
            "ax_state": text_state(accessible_name, **norm_kw),
            "has_icon": has_icon,
            "requires_reveal": requires_reveal,
        },
    }
    v_state = out["inputs"]["visible_state"]
    a_state = out["inputs"]["ax_state"]

    if requires_reveal is None:
        out["undeterminable_reason"] = "REVEAL_STATE_UNOBSERVED"
        return out
    if requires_reveal:
        # AMB-L-05: HIDDEN_UNTIL_REVEAL is taken as dominant over the icon/text axis.
        out["entry_label_modality"] = "HIDDEN_UNTIL_REVEAL"
        return out
    if v_state == "MISSING":
        out["undeterminable_reason"] = "VISIBLE_TEXT_UNOBSERVED"
        return out
    if has_icon is None:
        out["undeterminable_reason"] = "ICON_PRESENCE_UNOBSERVED"
        return out

    if v_state == "PRESENT":
        out["entry_label_modality"] = "ICON_TEXT" if has_icon else "EXPLICIT_TEXT"
        return out
    # v_state == EMPTY
    if not has_icon:
        # No visible text and no icon: the codebook has no member for this.
        out["undeterminable_reason"] = "NO_VISIBLE_TEXT_AND_NO_ICON"
        return out
    if a_state == "MISSING":
        out["undeterminable_reason"] = "AX_NAME_UNOBSERVED"
        return out
    if _m("M9_MERGE_ICON_ONLY"):
        out["entry_label_modality"] = "ICON_ONLY_AX_NAMED"
        return out
    out["entry_label_modality"] = (
        "ICON_ONLY_AX_NAMED" if a_state == "PRESENT" else "ICON_ONLY_UNNAMED"
    )
    return out


# --------------------------------------------------------------------------------------
# Row-level driver
# --------------------------------------------------------------------------------------
def compute_row(obs: LabelObservation, *, synonym_map: dict[str, str] | None = None) -> dict[str, Any]:
    rel = label_relation_all_readings(obs.visible_label_text, obs.accessible_name,
                                      synonym_map=synonym_map)
    src = accessible_name_source(obs.accessible_name, obs.name_source_candidates,
                                 observed=obs.accessible_name_source_observed)
    mod = entry_label_modality(obs.visible_label_text, obs.accessible_name,
                               has_icon=obs.has_icon, requires_reveal=obs.requires_reveal)
    return {
        "observation_id": obs.observation_id,
        "visible_label_text": obs.visible_label_text,
        "accessible_name": obs.accessible_name,
        "visible_label_state": rel["visible_state"],
        "accessible_name_state": rel["ax_state"],
        "label_relation": rel["label_relation"],
        "label_relation_undeterminable_reason": rel["undeterminable_reason"],
        "label_relation_readings": rel["readings"],
        "normalization_sensitive": rel["normalization_sensitive"],
        "diverging_readings": rel["diverging_readings"],
        "accessible_name_source": src["accessible_name_source"],
        "accessible_name_source_unresolved_reason": src["unresolved_reason"],
        "accessible_name_source_ambiguous": src["ambiguous"],
        "accessible_name_source_derivation": src["derivation"],
        "entry_label_modality": mod["entry_label_modality"],
        "entry_label_modality_undeterminable_reason": mod["undeterminable_reason"],
        "entry_control_type": obs.entry_control_type,
    }


# --------------------------------------------------------------------------------------
# Counterexample detectors
# --------------------------------------------------------------------------------------
def detect_same_ax_name_different_visible(
    observations: Iterable[LabelObservation], **norm_kw: Any
) -> list[dict[str, Any]]:
    """CE-1: the accessible name is the same but the visible label differs.

    Only PRESENT/PRESENT pairs participate; MISSING and EMPTY sides are excluded so an
    absence never manufactures a collision.
    """
    buckets: dict[str, list[tuple[str, str]]] = {}
    for o in observations:
        if text_state(o.accessible_name, **norm_kw) != "PRESENT":
            continue
        if text_state(o.visible_label_text, **norm_kw) != "PRESENT":
            continue
        key = o.accessible_name if _m("M10_RAW_KEYS") else normalize_text(o.accessible_name, **norm_kw)
        val = o.visible_label_text if _m("M10_RAW_KEYS") else normalize_text(o.visible_label_text, **norm_kw)
        buckets.setdefault(key, []).append((o.observation_id, val))  # type: ignore[arg-type]
    out = []
    for key, members in sorted(buckets.items()):
        forms = sorted({v for _, v in members})
        if len(forms) > 1:
            out.append({
                "accessible_name_normalized": key,
                "distinct_visible_forms": forms,
                "observation_ids": sorted(i for i, _ in members),
            })
    return out


def detect_same_visible_different_control_type(
    observations: Iterable[LabelObservation], **norm_kw: Any
) -> list[dict[str, Any]]:
    """CE-2: the visible label is the same but entry_control_type differs.

    entry_control_type is consumed as an opaque input string. This lane owns no control
    type taxonomy and reads no other lane's file.
    """
    buckets: dict[str, list[tuple[str, str]]] = {}
    for o in observations:
        if text_state(o.visible_label_text, **norm_kw) != "PRESENT":
            continue
        if o.entry_control_type is None:
            continue
        key = o.visible_label_text if _m("M10_RAW_KEYS") else normalize_text(o.visible_label_text, **norm_kw)
        buckets.setdefault(key, []).append((o.observation_id, o.entry_control_type))  # type: ignore[arg-type]
    out = []
    for key, members in sorted(buckets.items()):
        types = sorted({t for _, t in members})
        if len(types) > 1:
            out.append({
                "visible_label_normalized": key,
                "distinct_control_types": types,
                "observation_ids": sorted(i for i, _ in members),
            })
    return out


# --------------------------------------------------------------------------------------
# HTML evidence extraction (D-DEF-01 safe path)
# --------------------------------------------------------------------------------------
def extract_label_evidence_from_html(path: Path, xpath: str) -> dict[str, Any]:
    """Pull label evidence for one element out of a stored dom.html.

    ALWAYS routes through html_decode.parse_html. Never hand raw bytes to lxml.
    Returns the visible text and the naming-attribute candidates SEPARATELY; it does
    NOT compute an accessible name (that is the browser AX tree's job, 04 §7).
    """
    tree, enc = parse_html(Path(path))
    nodes = tree.xpath(xpath)
    if not nodes:
        return {"found": False, "encoding_used": enc, "xpath": xpath}
    el = nodes[0]
    labelledby_text = None
    ref = el.get("aria-labelledby")
    if ref:
        parts = []
        for rid in ref.split():
            tgt = tree.xpath(f'//*[@id="{rid}"]')
            if tgt:
                parts.append(tgt[0].text_content())
        labelledby_text = " ".join(parts) if parts else None
    img_alt = None
    imgs = el.xpath(".//img[@alt]")
    if imgs:
        img_alt = imgs[0].get("alt")
    return {
        "found": True,
        "encoding_used": enc,
        "xpath": xpath,
        "visible_label_text": el.text_content(),
        "name_source_candidates": {
            "ARIA_LABELLEDBY": labelledby_text,
            "ARIA_LABEL": el.get("aria-label"),
            "LABEL": None,
            "ALT": img_alt if img_alt is not None else el.get("alt"),
            "VALUE": el.get("value"),
            "VISIBLE_TEXT": el.text_content(),
            "TITLE": el.get("title"),
        },
    }


# --------------------------------------------------------------------------------------
# Ambiguity register
# --------------------------------------------------------------------------------------
AMBIGUOUS_DEFINITIONS = [
    {
        "id": "AMB-L-01",
        "variable": "label_relation",
        "question": "04 §5 says 'Unicode normalize' without naming the form. NFC (canonical) and NFKC (compatibility) disagree on fullwidth/halfwidth, circled and ligature forms.",
        "primary_reading_taken": "NFC",
        "competing_reading": "NFKC",
        "consequence": "Fullwidth vs ASCII labels are DIFFERENT under NFC and MATCH under NFKC.",
        "resolution_owner": "A",
    },
    {
        "id": "AMB-L-02",
        "variable": "label_relation",
        "question": "Is comparison case-sensitive? 04 §5 says 'exact' and never mentions case.",
        "primary_reading_taken": "case-sensitive (literal 'exact')",
        "competing_reading": "casefold before compare",
        "consequence": "'Search' vs 'search' is DIFFERENT under the primary reading.",
        "resolution_owner": "A",
    },
    {
        "id": "AMB-L-03",
        "variable": "label_relation / text_state",
        "question": "Are zero-width characters (U+200B/200C/200D/2060/FEFF) 'whitespace' for the whitespace-normalize step? They are not whitespace in Unicode, so str.split() keeps them.",
        "primary_reading_taken": "preserved (not whitespace)",
        "competing_reading": "stripped as invisible formatting",
        "consequence": "A ZWSP-only visible label is PRESENT under the primary reading and EMPTY under the competing one, which flips the row between DIFFERENT and AX_ONLY.",
        "resolution_owner": "A",
    },
    {
        "id": "AMB-L-04",
        "variable": "accessible_name_source",
        "question": "The codebook fixes the enum but not the attribution procedure. When two candidates hold the identical value that the AX name has, value evidence cannot separate them.",
        "primary_reading_taken": "attribute by unique value match; break exact-value ties with W3C accname 1.2 precedence and set accessible_name_source_ambiguous=true",
        "competing_reading": "leave unresolved whenever more than one candidate matches",
        "consequence": "Affects only rows flagged ambiguous; those rows are individually listed.",
        "resolution_owner": "A",
    },
    {
        "id": "AMB-L-05",
        "variable": "accessible_name_source",
        "question": "MIXED has no operational definition in 04 §4.",
        "primary_reading_taken": "MIXED iff the name equals the space-joined concatenation of 2-3 present candidate values (permutation search), which is the aria-labelledby multi-reference shape",
        "competing_reading": "MIXED only when the collector asserts it",
        "consequence": "Collector-asserted source always wins over derivation, so A can override wholesale.",
        "resolution_owner": "A",
    },
    {
        "id": "AMB-L-06",
        "variable": "entry_label_modality",
        "question": "Precedence between HIDDEN_UNTIL_REVEAL and the icon/text members is unspecified: a hidden control also has an icon/text character.",
        "primary_reading_taken": "HIDDEN_UNTIL_REVEAL dominates when requires_reveal is true",
        "competing_reading": "record reveal separately and keep the icon/text member",
        "consequence": "Icon-only rates in 05 §2-C will be understated for revealed controls under the primary reading.",
        "resolution_owner": "A",
    },
    {
        "id": "AMB-L-07",
        "variable": "entry_label_modality",
        "question": "No enum member covers 'no visible text and no icon' (e.g. a bare region or an unlabelled input).",
        "primary_reading_taken": "emit no value; undeterminable_reason=NO_VISIBLE_TEXT_AND_NO_ICON",
        "competing_reading": "extend the enum",
        "consequence": "Such rows are excluded from modality distributions rather than mislabelled.",
        "resolution_owner": "A",
    },
    {
        "id": "AMB-L-08",
        "variable": "label_relation",
        "question": "The enum has no member for 'a side was never observed'. NONE is defined as a relation, not as missingness.",
        "primary_reading_taken": "emit label_relation=null plus undeterminable_reason (BOTH/VISIBLE/AX_UNOBSERVED); NONE is reserved for observed-empty on both sides",
        "competing_reading": "map unobserved to NONE",
        "consequence": "The competing reading would inflate NONE and destroy the empty-vs-missing distinction the contract requires.",
        "resolution_owner": "A",
    },
    {
        "id": "AMB-L-09",
        "variable": "label_relation",
        "question": "Is NBSP (U+00A0) / ideographic space (U+3000) collapsed by 'whitespace normalize'? Both are Unicode whitespace, so Python's str.split() collapses them.",
        "primary_reading_taken": "collapsed",
        "competing_reading": "treat NBSP as a significant character",
        "consequence": "'검색\\u00a0하기' MATCHes '검색 하기' under the primary reading.",
        "resolution_owner": "A",
    },
    {
        "id": "AMB-L-10",
        "variable": "accessible_name_source",
        "question": "What does an observed-EMPTY accessible name mean when naming candidates are present (e.g. aria-label='' overriding real content)?",
        "primary_reading_taken": "unresolved; unresolved_reason=EMPTY_NAME_WITH_CANDIDATES (NOT the NONE member)",
        "competing_reading": "NONE",
        "consequence": "Keeps 'the AX tree computed nothing despite available sources' distinguishable from 'nothing was available'.",
        "resolution_owner": "A",
    },
]

# --------------------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------------------
NBSP = "\u00a0"
ZWSP = "\u200b"
KO_NFC = "검색"                       # U+AC80 U+C0C9
KO_NFD = unicodedata.normalize("NFD", "검색")
FULLWIDTH = "ＳＥＡＲＣＨ"
IDEOGRAPHIC_SPACE = "\u3000"

# (id, kwargs, expected primary label_relation, expected undeterminable_reason, must_not_be)
RELATION_FIXTURES: list[tuple[str, str | None, str | None, str | None, str | None, list[str]]] = [
    # --- exact / trivial -------------------------------------------------------------
    ("REL-01-identical-ko", KO_NFC, KO_NFC, "MATCH", None, ["DIFFERENT", "NONE"]),
    ("REL-02-plain-different-ko", "검색", "메뉴 열기", "DIFFERENT", None, ["MATCH", "SEMANTIC_EQUIV"]),
    # --- whitespace traps ------------------------------------------------------------
    ("REL-03-leading-trailing-space", "  검색  ", "검색", "MATCH", None, ["DIFFERENT"]),
    ("REL-04-internal-runs", "검색   하기", "검색 하기", "MATCH", None, ["DIFFERENT"]),
    ("REL-05-nbsp", f"검색{NBSP}하기", "검색 하기", "MATCH", None, ["DIFFERENT"]),
    ("REL-06-ideographic-space", f"검색{IDEOGRAPHIC_SPACE}하기", "검색 하기", "MATCH", None, ["DIFFERENT"]),
    ("REL-07-tab-newline", "검색\t\n하기", "검색 하기", "MATCH", None, ["DIFFERENT"]),
    # --- unicode composition ---------------------------------------------------------
    ("REL-08-nfc-vs-nfd", KO_NFC, KO_NFD, "MATCH", None, ["DIFFERENT"]),
    ("REL-09-nfd-both", KO_NFD, KO_NFD, "MATCH", None, ["DIFFERENT"]),
    # --- fullwidth (AMB-L-01) --------------------------------------------------------
    ("REL-10-fullwidth-vs-ascii", FULLWIDTH, "SEARCH", "DIFFERENT", None, ["MATCH"]),
    ("REL-11-fullwidth-digits", "１２３", "123", "DIFFERENT", None, ["MATCH"]),
    # --- case (AMB-L-02) -------------------------------------------------------------
    ("REL-12-case-differs", "Search", "search", "DIFFERENT", None, ["MATCH"]),
    ("REL-13-case-same", "Search", "Search", "MATCH", None, ["DIFFERENT"]),
    # --- zero width (AMB-L-03) -------------------------------------------------------
    ("REL-14-zwsp-inside", f"검{ZWSP}색", "검색", "DIFFERENT", None, ["MATCH"]),
    ("REL-15-bom-prefix", "\ufeff" + KO_NFC, "검색", "DIFFERENT", None, ["MATCH"]),
    ("REL-16-zwsp-only-visible", ZWSP, "검색", "DIFFERENT", None, ["AX_ONLY", "MATCH"]),
    # --- empty vs missing (contract requirement 4) -----------------------------------
    ("REL-17-visible-only", "검색", "", "VISIBLE_ONLY", None, ["MATCH", "NONE", "AX_ONLY"]),
    ("REL-18-ax-only", "", "검색", "AX_ONLY", None, ["MATCH", "NONE", "VISIBLE_ONLY"]),
    ("REL-19-both-empty-strings", "", "", "NONE", None, ["MATCH", "VISIBLE_ONLY", "AX_ONLY"]),
    ("REL-20-whitespace-only-both", "   ", "\t", "NONE", None, ["MATCH", "DIFFERENT"]),
    ("REL-21-visible-missing", None, "검색", None, "VISIBLE_UNOBSERVED", ["AX_ONLY", "NONE"]),
    ("REL-22-ax-missing", "검색", None, None, "AX_UNOBSERVED", ["VISIBLE_ONLY", "NONE"]),
    ("REL-23-both-missing", None, None, None, "BOTH_UNOBSERVED", ["NONE", "MATCH"]),
    ("REL-24-visible-missing-ax-empty", None, "", None, "VISIBLE_UNOBSERVED", ["NONE"]),
    ("REL-25-visible-empty-ax-missing", "", None, None, "AX_UNOBSERVED", ["NONE"]),
    # --- synonym map is empty: no SEMANTIC_EQUIV on real data ------------------------
    ("REL-26-no-synonym-merge", "조회", "검색", "DIFFERENT", None, ["SEMANTIC_EQUIV", "MATCH"]),
    ("REL-27-near-miss-not-merged", "검색하기", "검색", "DIFFERENT", None, ["MATCH", "SEMANTIC_EQUIV"]),
    ("REL-28-substring-not-merged", "검색", "통합 검색", "DIFFERENT", None, ["MATCH", "SEMANTIC_EQUIV"]),
    # --- mixed traps -----------------------------------------------------------------
    ("REL-29-nfd-plus-whitespace", f"  {KO_NFD}{NBSP}하기 ", "검색 하기", "MATCH", None, ["DIFFERENT"]),
    ("REL-30-emoji-icon-text", "🔍", "검색", "DIFFERENT", None, ["MATCH"]),
]

# (id, ax_name, candidates, expected source, expected unresolved reason)
SOURCE_FIXTURES: list[tuple[str, str | None, dict[str, str | None] | None, str | None, str | None]] = [
    ("SRC-01-aria-label", "메뉴 열기",
     {"ARIA_LABEL": "메뉴 열기", "VISIBLE_TEXT": ""}, "ARIA_LABEL", None),
    ("SRC-02-visible-text", "검색",
     {"ARIA_LABEL": None, "VISIBLE_TEXT": "검색"}, "VISIBLE_TEXT", None),
    ("SRC-03-alt", "노선도",
     {"ALT": "노선도", "VISIBLE_TEXT": ""}, "ALT", None),
    ("SRC-04-title-only", "도움말",
     {"TITLE": "도움말", "VISIBLE_TEXT": ""}, "TITLE", None),
    ("SRC-05-value", "조회",
     {"VALUE": "조회", "VISIBLE_TEXT": ""}, "VALUE", None),
    ("SRC-06-label", "출발역",
     {"LABEL": "출발역", "VISIBLE_TEXT": ""}, "LABEL", None),
    ("SRC-07-labelledby", "빠른 예매",
     {"ARIA_LABELLEDBY": "빠른 예매", "VISIBLE_TEXT": ""}, "ARIA_LABELLEDBY", None),
    ("SRC-08-tie-aria-label-wins", "검색",
     {"ARIA_LABEL": "검색", "VISIBLE_TEXT": "검색", "TITLE": "검색"}, "ARIA_LABEL", None),
    ("SRC-09-mixed-concat", "출발역 도착역",
     {"ARIA_LABELLEDBY": None, "LABEL": "출발역", "TITLE": "도착역"}, "MIXED", None),
    ("SRC-10-none-empty-no-candidates", "", {"ARIA_LABEL": None, "VISIBLE_TEXT": ""}, "NONE", None),
    ("SRC-11-empty-with-candidates", "",
     {"ARIA_LABEL": "메뉴", "VISIBLE_TEXT": ""}, None, "EMPTY_NAME_WITH_CANDIDATES"),
    ("SRC-12-ax-missing", None, {"ARIA_LABEL": "메뉴"}, None, "AX_NAME_UNOBSERVED"),
    ("SRC-13-candidates-missing", "검색", None, None, "CANDIDATES_UNOBSERVED"),
    ("SRC-14-not-attributable", "검색",
     {"ARIA_LABEL": "메뉴", "VISIBLE_TEXT": "홈"}, None, "NAME_NOT_ATTRIBUTABLE"),
    ("SRC-15-normalized-match", f"  검색{NBSP}하기 ",
     {"ARIA_LABEL": "검색 하기", "VISIBLE_TEXT": ""}, "ARIA_LABEL", None),
    ("SRC-16-nfd-candidate", KO_NFC,
     {"ARIA_LABEL": KO_NFD, "VISIBLE_TEXT": ""}, "ARIA_LABEL", None),
]

# (id, visible, ax, has_icon, requires_reveal, expected modality, expected reason)
MODALITY_FIXTURES: list[tuple[str, str | None, str | None, bool | None, bool | None, str | None, str | None]] = [
    ("MOD-01-explicit-text", "지하철 노선도", "지하철 노선도", False, False, "EXPLICIT_TEXT", None),
    ("MOD-02-icon-text", "검색", "검색", True, False, "ICON_TEXT", None),
    ("MOD-03-icon-only-ax-named", "", "검색", True, False, "ICON_ONLY_AX_NAMED", None),
    ("MOD-04-icon-only-unnamed-empty-ax", "", "", True, False, "ICON_ONLY_UNNAMED", None),
    ("MOD-05-icon-only-ax-missing", "", None, True, False, None, "AX_NAME_UNOBSERVED"),
    ("MOD-06-hidden-until-reveal", "", "전체메뉴", True, True, "HIDDEN_UNTIL_REVEAL", None),
    ("MOD-07-hidden-dominates-text", "전체메뉴", "전체메뉴", False, True, "HIDDEN_UNTIL_REVEAL", None),
    ("MOD-08-no-text-no-icon", "", "", False, False, None, "NO_VISIBLE_TEXT_AND_NO_ICON"),
    ("MOD-09-visible-missing", None, "검색", True, False, None, "VISIBLE_TEXT_UNOBSERVED"),
    ("MOD-10-icon-unobserved", "", "검색", None, False, None, "ICON_PRESENCE_UNOBSERVED"),
    ("MOD-11-reveal-unobserved", "검색", "검색", False, None, None, "REVEAL_STATE_UNOBSERVED"),
    ("MOD-12-whitespace-only-visible-is-empty", "   ", "검색", True, False, "ICON_ONLY_AX_NAMED", None),
    ("MOD-13-zwsp-visible-counts-as-present", ZWSP, "검색", True, False, "ICON_TEXT", None),
    ("MOD-14-ax-whitespace-only-unnamed", "", "  ", True, False, "ICON_ONLY_UNNAMED", None),
]

CE_FIXTURE_OBSERVATIONS = [
    # CE-1 positive: two different visible labels, identical AX name
    LabelObservation("ce-a1", "예매", "승차권 예매", entry_control_type="TEXT_BUTTON"),
    LabelObservation("ce-a2", "표 사기", "승차권 예매", entry_control_type="TEXT_LINK"),
    # CE-1 normalization-only difference must NOT count as a different visible form
    LabelObservation("ce-a3", f"승차권{NBSP}예매", "예매하기", entry_control_type="TEXT_LINK"),
    LabelObservation("ce-a4", "승차권 예매", "예매하기", entry_control_type="TEXT_LINK"),
    # CE-1 negative: same AX name, same visible label
    LabelObservation("ce-b1", "노선도", "노선도", entry_control_type="CARD"),
    LabelObservation("ce-b2", "노선도", "노선도", entry_control_type="CARD"),
    # CE-1 must ignore EMPTY/MISSING sides
    LabelObservation("ce-c1", "", "지도", entry_control_type="ICON_ONLY"),
    LabelObservation("ce-c2", None, "지도", entry_control_type="ICON_ONLY"),
    # CE-2 positive: same visible label, different control type
    LabelObservation("ce-d1", "검색", "검색", entry_control_type="SEARCHBOX"),
    LabelObservation("ce-d2", "검색", "통합검색", entry_control_type="ICON_ONLY"),
    # CE-2 must ignore rows with no control type
    LabelObservation("ce-e1", "고객센터", "고객센터", entry_control_type=None),
    LabelObservation("ce-e2", "고객센터", "고객센터", entry_control_type="TEXT_LINK"),
]

MUTATIONS = {
    "M1_NO_WHITESPACE_COLLAPSE": "drop the whitespace-normalize step",
    "M2_NFKC_PRIMARY": "use NFKC as the primary normalization form",
    "M3_CASEFOLD_PRIMARY": "casefold before the exact compare",
    "M4_NO_UNICODE_NORMALIZE": "skip Unicode normalization entirely",
    "M5_EMPTY_IS_MISSING": "collapse observed-EMPTY into MISSING",
    "M6_NO_MIXED": "never derive MIXED",
    "M7_STRIP_ZERO_WIDTH": "strip zero-width characters in the primary reading",
    "M8_REVERSE_PRECEDENCE": "reverse the accname tie-break precedence",
    "M9_MERGE_ICON_ONLY": "merge ICON_ONLY_UNNAMED into ICON_ONLY_AX_NAMED",
    "M10_RAW_KEYS": "group counterexamples on raw (unnormalized) text",
    "M11_ONLY_SIDE_COLLAPSE": "emit VISIBLE_ONLY for both one-sided cases (breaks the mirror)",
    "M12_AX_FALLBACK_TO_VISIBLE": "back-fill a missing accessible_name from visible_label_text "
                                  "-- the exact merge SSOT 00 §8 forbids",
}


# --------------------------------------------------------------------------------------
# Korean HTML round-trip fixtures (D-DEF-01 regression)
# --------------------------------------------------------------------------------------
HTML_FIXTURES = [
    ("utf8", "utf-8", "<meta charset=\"UTF-8\">"),
    ("euckr", "euc-kr", "<meta charset=\"euc-kr\">"),
    ("cp949", "cp949", "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=cp949\">"),
    # No in-document declaration. This is the case that actually reproduces D-DEF-01:
    # libxml2 falls back to Latin-1 for undeclared bytes. See LANE_L_FINDINGS.md.
    ("utf8_no_declaration", "utf-8", ""),
]
HTML_BODY_TMPL = (
    "<html><head>{meta}<title>승차권 예매</title></head><body>"
    "<span id=\"lb1\">출발역</span>"
    "<a id=\"t1\" href=\"/x\" aria-label=\"승차권 예매 바로가기\" title=\"예매\">"
    "<img src=\"i.png\" alt=\"예매 아이콘\"> 승차권 예매</a>"
    "<button id=\"t2\" aria-labelledby=\"lb1\"><img src=\"j.png\" alt=\"\"></button>"
    "</body></html>"
)


def _write_html_fixtures(dest: Path) -> list[dict[str, Any]]:
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for name, enc, meta in HTML_FIXTURES:
        p = dest / f"lane_l_ko_{name}.html"
        p.write_bytes(HTML_BODY_TMPL.format(meta=meta).encode(enc))
        written.append({"name": name, "declared_encoding": enc, "path": str(p)})
    return written


def _run_html_roundtrip(dest: Path) -> dict[str, Any]:
    written = _write_html_fixtures(dest)
    cases = []
    for w in written:
        ev = extract_label_evidence_from_html(Path(w["path"]), '//a[@id="t1"]')
        ev2 = extract_label_evidence_from_html(Path(w["path"]), '//button[@id="t2"]')
        vis = normalize_text(ev["visible_label_text"])
        aria = ev["name_source_candidates"]["ARIA_LABEL"]
        alt = ev["name_source_candidates"]["ALT"]
        lb = ev2["name_source_candidates"]["ARIA_LABELLEDBY"]
        ok = (vis == "승차권 예매" and aria == "승차권 예매 바로가기"
              and alt == "예매 아이콘" and normalize_text(lb) == "출발역"
              and "�" not in (ev["visible_label_text"] or "")
              and "Ã" not in (ev["visible_label_text"] or ""))
        # the same element, run through the whole calculator
        row = compute_row(LabelObservation(
            observation_id=f"html-{w['name']}",
            visible_label_text=ev["visible_label_text"],
            accessible_name=aria,
            name_source_candidates=ev["name_source_candidates"],
            has_icon=True, requires_reveal=False, entry_control_type="ICON_TEXT",
        ))
        cases.append({
            "fixture": w["name"], "declared_encoding": w["declared_encoding"],
            "encoding_used": ev["encoding_used"],
            "visible_label_text": ev["visible_label_text"],
            "aria_label": aria, "alt": alt, "aria_labelledby_text": lb,
            "mojibake_free": ok,
            "label_relation": row["label_relation"],
            "accessible_name_source": row["accessible_name_source"],
            "entry_label_modality": row["entry_label_modality"],
            "pass": bool(ok and row["label_relation"] == "DIFFERENT"
                         and row["accessible_name_source"] == "ARIA_LABEL"
                         and row["entry_label_modality"] == "ICON_TEXT"),
        })
    # negative control: the D-DEF-01 defect itself
    from lxml import html as lxml_html
    neg = []
    for name, _enc, _meta in HTML_FIXTURES:
        raw = (dest / f"lane_l_ko_{name}.html").read_bytes()
        bad = lxml_html.fromstring(raw).xpath('//a[@id="t1"]')[0].text_content()
        good = extract_label_evidence_from_html(
            dest / f"lane_l_ko_{name}.html", '//a[@id="t1"]')["visible_label_text"]
        neg.append({
            "fixture": name,
            "bytes_to_lxml_text": bad.strip()[:80],
            "bytes_to_lxml_mojibake": normalize_text(bad) != "승차권 예매",
            "parse_html_text": (good or "").strip()[:80],
            "parse_html_correct": normalize_text(good) == "승차권 예매",
        })
    return {
        "cases": cases,
        "passed": sum(1 for c in cases if c["pass"]),
        "total": len(cases),
        "negative_control_bytes_to_lxml": neg,
        "negative_control_bytes_to_lxml_produces_mojibake": any(
            n["bytes_to_lxml_mojibake"] for n in neg),
        "negative_control_parse_html_always_correct": all(
            n["parse_html_correct"] for n in neg),
        "d_def_01_trigger_refinement": (
            "With lxml %s, handing raw bytes to lxml.html.fromstring only produces mojibake "
            "when the document carries NO in-document charset declaration (libxml2 then "
            "defaults to Latin-1). Declared UTF-8, euc-kr and cp949 all decode correctly even "
            "from bytes. So the D-DEF-01 defect is real but its stated mechanism ('lxml ignored "
            "the declared charset') does not reproduce here; the reproducing condition is an "
            "ABSENT declaration. D has NOT inspected the real dom.html files, so this is a "
            "fixture-level observation about the parser, not a re-attribution of the original "
            "6/56 incident."
        ) % __import__("lxml").__version__,
    }


# --------------------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------------------
def _relation_case(fx) -> dict[str, Any]:
    fid, vis, ax, exp_rel, exp_reason, must_not = fx
    got = label_relation_all_readings(vis, ax)
    ok = (got["label_relation"] == exp_rel
          and got["undeterminable_reason"] == exp_reason
          and got["label_relation"] not in must_not)
    return {
        "fixture_id": fid, "visible_repr": repr(vis), "ax_repr": repr(ax),
        "expected": exp_rel, "expected_reason": exp_reason,
        "got": got["label_relation"], "got_reason": got["undeterminable_reason"],
        "must_not_be": must_not,
        "visible_state": got["visible_state"], "ax_state": got["ax_state"],
        "readings": got["readings"], "normalization_sensitive": got["normalization_sensitive"],
        "diverging_readings": got["diverging_readings"],
        "pass": ok,
    }


def _source_case(fx) -> dict[str, Any]:
    fid, ax, cands, exp, exp_reason = fx
    got = accessible_name_source(ax, cands)
    ok = got["accessible_name_source"] == exp and got["unresolved_reason"] == exp_reason
    return {"fixture_id": fid, "expected": exp, "expected_reason": exp_reason,
            "got": got["accessible_name_source"], "got_reason": got["unresolved_reason"],
            "matched_sources": got["matched_sources"], "ambiguous": got["ambiguous"],
            "derivation": got["derivation"], "pass": ok}


def _modality_case(fx) -> dict[str, Any]:
    fid, vis, ax, icon, reveal, exp, exp_reason = fx
    got = entry_label_modality(vis, ax, has_icon=icon, requires_reveal=reveal)
    ok = got["entry_label_modality"] == exp and got["undeterminable_reason"] == exp_reason
    return {"fixture_id": fid, "expected": exp, "expected_reason": exp_reason,
            "got": got["entry_label_modality"], "got_reason": got["undeterminable_reason"],
            "inputs": got["inputs"], "pass": ok}


def _ce_expectations() -> dict[str, Any]:
    ce1 = detect_same_ax_name_different_visible(CE_FIXTURE_OBSERVATIONS)
    ce2 = detect_same_visible_different_control_type(CE_FIXTURE_OBSERVATIONS)
    ce1_keys = {g["accessible_name_normalized"]: g for g in ce1}
    ce2_keys = {g["visible_label_normalized"]: g for g in ce2}
    checks = [
        ("CE1-positive-detected", "승차권 예매" in ce1_keys),
        ("CE1-positive-members", ce1_keys.get("승차권 예매", {}).get("observation_ids") == ["ce-a1", "ce-a2"]),
        ("CE1-nbsp-not-a-difference", "예매하기" not in ce1_keys),
        ("CE1-identical-not-flagged", "노선도" not in ce1_keys),
        ("CE1-empty-and-missing-ignored", "지도" not in ce1_keys),
        ("CE2-positive-detected", "검색" in ce2_keys),
        ("CE2-positive-types", ce2_keys.get("검색", {}).get("distinct_control_types") == ["ICON_ONLY", "SEARCHBOX"]),
        ("CE2-null-control-type-ignored", "고객센터" not in ce2_keys),
        ("CE2-same-type-not-flagged", "노선도" not in ce2_keys),
    ]
    return {
        "ce1_same_ax_name_different_visible_label": ce1,
        "ce2_same_visible_label_different_control_type": ce2,
        "checks": [{"check": n, "pass": bool(v)} for n, v in checks],
        "passed": sum(1 for _, v in checks if v),
        "total": len(checks),
    }


def _synonym_path_test() -> dict[str, Any]:
    """Proves SEMANTIC_EQUIV is reachable in code but unreachable with the shipped map."""
    with_empty = label_relation("조회", "검색")["label_relation"]
    test_map = {"조회": "CONCEPT_TEST", "검색": "CONCEPT_TEST"}  # TEST_ONLY_NOT_AUTHORITATIVE
    with_map = label_relation("조회", "검색", synonym_map=test_map)["label_relation"]
    unrelated = label_relation("조회", "로그인", synonym_map=test_map)["label_relation"]
    return {
        "shipped_map_size": len(SYNONYM_MAP),
        "shipped_map_result": with_empty,
        "injected_test_map_result": with_map,
        "injected_map_unrelated_pair_result": unrelated,
        "note": "the injected map is TEST_ONLY_NOT_AUTHORITATIVE; A owns the real map",
        "pass": with_empty == "DIFFERENT" and with_map == "SEMANTIC_EQUIV" and unrelated == "DIFFERENT",
    }


MIRROR_RELATION = {
    "MATCH": "MATCH", "DIFFERENT": "DIFFERENT", "SEMANTIC_EQUIV": "SEMANTIC_EQUIV",
    "NONE": "NONE", "VISIBLE_ONLY": "AX_ONLY", "AX_ONLY": "VISIBLE_ONLY", None: None,
}
MIRROR_REASON = {
    "VISIBLE_UNOBSERVED": "AX_UNOBSERVED", "AX_UNOBSERVED": "VISIBLE_UNOBSERVED",
    "BOTH_UNOBSERVED": "BOTH_UNOBSERVED", None: None,
}


def _symmetry_test() -> dict[str, Any]:
    """Bidirectional check: swapping the two sides must mirror the relation exactly.

    Catches an argument-order bug that the one-directional fixtures alone cannot see,
    and pins that VISIBLE_ONLY/AX_ONLY are genuine mirrors rather than a default branch.
    """
    rows = []
    for fid, vis, ax, _e, _r, _mn in RELATION_FIXTURES:
        fwd = label_relation(vis, ax)
        rev = label_relation(ax, vis)
        ok = (rev["label_relation"] == MIRROR_RELATION[fwd["label_relation"]]
              and rev["undeterminable_reason"] == MIRROR_REASON[fwd["undeterminable_reason"]])
        rows.append({"fixture_id": fid,
                     "forward": [fwd["label_relation"], fwd["undeterminable_reason"]],
                     "reversed": [rev["label_relation"], rev["undeterminable_reason"]],
                     "pass": ok})
    return {"cases": rows, "passed": sum(1 for r in rows if r["pass"]), "total": len(rows),
            "failed": [r["fixture_id"] for r in rows if not r["pass"]]}


def _all_cases() -> list[dict[str, Any]]:
    return ([_relation_case(f) for f in RELATION_FIXTURES]
            + [_source_case(f) for f in SOURCE_FIXTURES]
            + [_modality_case(f) for f in MODALITY_FIXTURES])


def _mutation_test() -> dict[str, Any]:
    baseline = _all_cases()
    baseline_fail = [c["fixture_id"] for c in baseline if not c["pass"]]
    results = []
    for mut, desc in MUTATIONS.items():
        with mutation(mut):
            cases = _all_cases()
            ce = _ce_expectations()
            sym = _symmetry_test()
        killed_fixtures = [c["fixture_id"] for c in cases if not c["pass"]]
        killed_ce = [c["check"] for c in ce["checks"] if not c["pass"]]
        results.append({
            "mutation": mut, "description": desc,
            "killed_by_fixtures": killed_fixtures,
            "killed_by_counterexample_checks": killed_ce,
            "killed_by_swap_symmetry": sym["failed"],
            "killed": bool(killed_fixtures or killed_ce or sym["failed"]),
        })
    # restore check
    after = _all_cases()
    restored = (
        [(c["fixture_id"], c["pass"], c["got"], c.get("got_reason")) for c in after]
        == [(c["fixture_id"], c["pass"], c["got"], c.get("got_reason")) for c in baseline]
        and not _MUT and not baseline_fail
    )
    return {
        "mutations": results,
        "killed": sum(1 for r in results if r["killed"]),
        "total": len(results),
        "survivors": [r["mutation"] for r in results if not r["killed"]],
        "restored_to_baseline_after_mutations": restored,
    }


def _enum_coverage(cases: list[dict[str, Any]]) -> dict[str, Any]:
    got_rel = {c["got"] for c in cases if c["fixture_id"].startswith("REL-")}
    got_src = {c["got"] for c in cases if c["fixture_id"].startswith("SRC-")}
    got_mod = {c["got"] for c in cases if c["fixture_id"].startswith("MOD-")}
    return {
        "label_relation": {"enum": list(LABEL_RELATION),
                           "exercised": sorted(x for x in got_rel if x),
                           "unexercised": sorted(set(LABEL_RELATION) - got_rel)},
        "accessible_name_source": {"enum": list(ACCESSIBLE_NAME_SOURCE),
                                   "exercised": sorted(x for x in got_src if x),
                                   "unexercised": sorted(set(ACCESSIBLE_NAME_SOURCE) - got_src)},
        "entry_label_modality": {"enum": list(ENTRY_LABEL_MODALITY),
                                 "exercised": sorted(x for x in got_mod if x),
                                 "unexercised": sorted(set(ENTRY_LABEL_MODALITY) - got_mod)},
    }


def _codebook_verbatim() -> dict[str, Any]:
    text = CODEBOOK.read_text(encoding="utf-8")
    lines = text.splitlines()
    wanted = ("entry_label_modality", "visible_label_text", "| `accessible_name`",
              "accessible_name_source", "label_relation", "entry_control_type")
    rows = [ln for ln in lines if ln.startswith("| `") and any(w in ln for w in wanted)]
    sec7 = text.split("## 7. Accessible name", 1)[1].strip() if "## 7. Accessible name" in text else None
    rule5 = next((ln for ln in lines if ln.strip().startswith("- `label_relation`")), None)
    return {
        "source_file": str(CODEBOOK),
        "sha256": hashlib.sha256(CODEBOOK.read_bytes()).hexdigest(),
        "section_4_variable_rows": rows,
        "section_5_label_relation_rule": rule5,
        "section_7_accessible_name": sec7,
        "ssot_00_section_8": (SSOT_DIR / "00_SSOT_v3.0_CROSS_SERVICE_FLOW.md")
        .read_text(encoding="utf-8").split("## 8. Visible Label / Accessible Name 분리", 1)[1]
        .split("---", 1)[0].strip(),
    }


def run_selftest() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = _all_cases()
    ce = _ce_expectations()
    syn = _synonym_path_test()
    sym = _symmetry_test()
    html = _run_html_roundtrip(OUT_DIR / "fixtures")
    mut = _mutation_test()
    cov = _enum_coverage(cases)

    fixture_pass = sum(1 for c in cases if c["pass"])
    all_green = (fixture_pass == len(cases)
                 and ce["passed"] == ce["total"]
                 and syn["pass"]
                 and sym["passed"] == sym["total"]
                 and html["passed"] == html["total"]
                 and html["negative_control_bytes_to_lxml_produces_mojibake"]
                 and html["negative_control_parse_html_always_correct"]
                 and mut["killed"] == mut["total"]
                 and mut["restored_to_baseline_after_mutations"])

    verdict = "READY" if (all_green and not AMBIGUOUS_DEFINITIONS) else (
        "READY_WITH_AMBIGUITY" if all_green else "NOT_READY")

    doc = {
        "lane": "L",
        "artifact": "LANE_L_HARNESS",
        "generated_by": str(Path(__file__).resolve()),
        "base_sha": "7448184a811f5d7d8772f21488bb75418fde3313",
        "ssot_manifest_sha256": "1735c956d4a3461ee9eb2543c5c474942887bcbd117f5876d5486207f2f72e0a",
        "verdict": verdict,
        "verdict_basis": {
            "all_fixture_checks_green": all_green,
            "fixture_pass": fixture_pass, "fixture_total": len(cases),
            "counterexample_checks_pass": ce["passed"], "counterexample_checks_total": ce["total"],
            "swap_symmetry_pass": sym["passed"], "swap_symmetry_total": sym["total"],
            "mutation_killed": mut["killed"], "mutation_total": mut["total"],
            "open_ambiguities": len(AMBIGUOUS_DEFINITIONS),
            "note": "READY is withheld because the codebook under-specifies the points in "
                    "ambiguous_definitions; every one of them changes real output. The "
                    "calculator runs and is self-consistent, but the primary readings are "
                    "D's literal reading, not an A ruling.",
        },
        "codebook_definitions_verbatim": _codebook_verbatim(),
        "implemented_variables": {
            "count": 5,
            "variables": [
                {"name": "visible_label_text", "role": "pass-through + state classification "
                 "(MISSING/EMPTY/PRESENT) + normalization; never merged with accessible_name"},
                {"name": "accessible_name", "role": "pass-through + state classification; "
                 "this module does NOT run AX naming computation (04 §7 assigns it to the browser)"},
                {"name": "accessible_name_source", "role": "derived, evidence-first attribution "
                 "over the frozen 9-member enum; unresolved instead of guessed"},
                {"name": "label_relation", "role": "derived, 6-member enum, normalize+exact, "
                 "synonym-map-only semantic equivalence"},
                {"name": "entry_label_modality", "role": "derived, 5-member enum, "
                 "ICON_ONLY_AX_NAMED vs ICON_ONLY_UNNAMED separated by AX name state"},
            ],
            "input_only_fields": [
                {"name": "entry_control_type", "note": "consumed opaquely by CE-2; this lane "
                 "defines no control-type taxonomy and reads no other lane's file"},
            ],
            "enum_coverage": cov,
            "enum_coverage_note": (
                "label_relation.SEMANTIC_EQUIV is deliberately unexercised by the main fixture "
                "set: the shipped synonym map is empty, so the member is unreachable until A "
                "authors one. Its code path is proved separately in "
                "fixture_results.synonym_map_code_path using a TEST_ONLY map."
            ),
        },
        "fixture_results": {
            "positive_and_negative": {
                "total": len(cases), "passed": fixture_pass,
                "failed": [c for c in cases if not c["pass"]],
                "cases": cases,
            },
            "counterexample_fixtures": ce,
            "swap_symmetry": sym,
            "synonym_map_code_path": syn,
            "korean_html_roundtrip": html,
            "mutation": mut,
        },
        "ambiguous_definitions": AMBIGUOUS_DEFINITIONS,
        "counterexample_detectors": [
            {"id": "CE-1", "function": "detect_same_ax_name_different_visible",
             "definition": "group observations whose accessible_name is PRESENT by its normalized "
                           "form; flag groups holding more than one distinct normalized "
                           "visible_label_text (also PRESENT). EMPTY and MISSING sides are excluded "
                           "so an absence can never manufacture a collision.",
             "no_threshold": True},
            {"id": "CE-2", "function": "detect_same_visible_different_control_type",
             "definition": "group observations whose visible_label_text is PRESENT by its "
                           "normalized form; flag groups holding more than one distinct "
                           "entry_control_type. entry_control_type is an opaque input string.",
             "no_threshold": True,
             "interface_note": "control type arrives on LabelObservation.entry_control_type; "
                               "no Lane S file is read or written."},
        ],
        "limitation": [
            "MAIN50 has no measured data yet; every result here is from synthetic fixtures. "
            "Nothing in this file has touched a real service.",
            "This module does not compute accessible names. It consumes the AX name the collector "
            "recorded. If the collector's AX capture is wrong, every derived value here is wrong "
            "in the same direction and the harness cannot see it.",
            "accessible_name_source attribution is evidence-based string matching against the "
            "candidate values the collector stored. A name produced by a naming path the collector "
            "did not record (e.g. a pseudo-element, a shadow-DOM label, an implicit table/legend "
            "name) will come back NAME_NOT_ATTRIBUTABLE, not wrong-but-plausible.",
            "The synonym map is empty by contract, so SEMANTIC_EQUIV cannot occur on real data "
            "until A supplies an authored map. Until then every real semantic pair lands in "
            "DIFFERENT and the DIFFERENT bucket is inflated by exactly that amount.",
            "Whitespace normalization uses Python str.split() semantics, which collapse every "
            "Unicode whitespace character including NBSP and U+3000 (AMB-L-09).",
            "The HTML extraction helper reads a single element by xpath. It is a decoding-safety "
            "and evidence-shape test, not a candidate-binding implementation.",
            "Fixture expectations were authored by D from the codebook text. They encode D's "
            "literal reading; where that reading is contested it is registered in "
            "ambiguous_definitions rather than defended.",
        ],
        "not_implemented": [
            "AX naming computation (browser's job per 04 §7)",
            "entry_control_type classification (other lane's taxonomy)",
            "any threshold, similarity cutoff, or composite score",
            "embedding / fuzzy / edit-distance label merging (forbidden by 04 §5)",
            "populating the synonym map (A's authority)",
            "icon-only rate, unique-form counts, or any 05 §2-C aggregate (needs MAIN50 data)",
            "gold labels, task gold, holdout access, GO/NO-GO calls",
            "MLflow logging, git operations, REAL service access",
        ],
    }
    return doc


def main() -> int:
    doc = run_selftest()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LANE_L_HARNESS.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "verdict": doc["verdict"],
        "fixtures": f'{doc["verdict_basis"]["fixture_pass"]}/{doc["verdict_basis"]["fixture_total"]}',
        "symmetry": f'{doc["verdict_basis"]["swap_symmetry_pass"]}/{doc["verdict_basis"]["swap_symmetry_total"]}',
        "ce_checks": f'{doc["verdict_basis"]["counterexample_checks_pass"]}/{doc["verdict_basis"]["counterexample_checks_total"]}',
        "mutations_killed": f'{doc["verdict_basis"]["mutation_killed"]}/{doc["verdict_basis"]["mutation_total"]}',
        "survivors": doc["fixture_results"]["mutation"]["survivors"],
        "html": f'{doc["fixture_results"]["korean_html_roundtrip"]["passed"]}/{doc["fixture_results"]["korean_html_roundtrip"]["total"]}',
        "failed_fixtures": [c["fixture_id"] for c in doc["fixture_results"]["positive_and_negative"]["failed"]],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
