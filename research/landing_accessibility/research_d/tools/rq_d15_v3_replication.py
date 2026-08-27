"""RQ-D15 — v3 코퍼스에서 D 의 NLP 계열 결론이 살아남는가 (자기 반증 시도).

D 는 자기 코퍼스 빌더에서 결함 두 개를 찾아 고쳤다.
  D-DEF-01  lxml.html.fromstring(read_bytes()) 가 선언 charset(UTF-8)을 무시 → 한글 mojibake
            (v2 에서 시정)
  D-DEF-04  text_content() 가 중첩된 <style>/<script>/<noscript>/<template> 텍스트를 포함
            → CSS 선언이 landmarks/buttons 로 유출 (v3 에서 시정)

NLP 계열 실험(RF001-B, RF001-C, RF2-C, D-SUP-01)은 전부 오염된 코퍼스(v1 또는 v2)로 돌았다.
이 스크립트는 **기존 산출물을 고치지 않고** 같은 사전등록 판정 규칙을 v1/v2/v3 에 그대로
다시 적용해 **판정(verdict)** 이 뒤집히는지를 본다. 수치가 아니라 판정이 답이다.

D-FACT-01 (프레이밍, 반드시 반복)
--------------------------------
이 56 target 표본에서 prior_archetype 과 prior_business_domain 은 완전 전단사다
(7↔7, MI = H = 2.311 bits, nMI 1.000, 56/56). 따라서 여기 나오는 모든 prior_agreement 는
**"업종 배정 재현율"** 이지 대표기능 정확도가 아니다. accuracy 라고 부르지 않는다.

research firewall
-----------------
이 스크립트는 holdout label 스냅샷 · LABEL_SPLIT_FROZEN* · HOLDOUT_FOR_C* · RAW_L1~L4* ·
PACKET_L* · *_OVERLAP* · PRECEDENCE_CONTESTED* · CALIBRATION_FOR_B* · **/control/** 를
not_opened — 하나도 열지 않았다. 입력은 아래 INPUTS 에 열거된 D 자체 산출물뿐이다.
gold label 을 만들지 않고, REAL_TARGET 에 접속하지 않으며, 네트워크 다운로드를 하지 않는다.
threshold 나 GO/NO-GO 는 선언하지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import pandas as pd

RD = Path("/home/sieg/projects-wsl/ProjectFinal/.agent_worktrees/claude_d_research"
          "/research/landing_accessibility/research_d")
RES = RD / "results"
FIGDIR = RD / "figures"
OUT_JSON = RES / "RQ_D15_v3_replication.json"

SEED = 20260827
N_MC = 20000
N_PERM_TFIDF = 200
N_BOOT = 4000
KST = timezone(timedelta(hours=9))

VERSIONS = ("v1", "v2", "v3")
CORPUS_PATH = {"v1": RES / "D_TEXT_CORPUS.csv",
               "v2": RES / "D_TEXT_CORPUS_v2.csv",
               "v3": RES / "D_TEXT_CORPUS_v3.csv"}
INPUTS = {
    "corpus_v1": CORPUS_PATH["v1"],
    "corpus_v2": CORPUS_PATH["v2"],
    "corpus_v3": CORPUS_PATH["v3"],
    "observation_table_v2": RES / "D_OBSERVATION_TABLE_v2.csv",
    "d14_frame_validity": RES / "RQ_D14_frame_validity.json",
}

ARCHETYPES = ["QUERY", "CONTENT_OPEN", "ITEM_DETAIL", "PLACE_LOOKUP",
              "COMMUNICATION_ENTRY", "FINANCIAL_ACTION_ENTRY", "UTILITY_ENTRY"]
A2I = {a: i for i, a in enumerate(ARCHETYPES)}
TOK = re.compile(r"[a-zA-Z0-9가-힣]+")
HANGUL = re.compile(r"[가-힣]")
FIELDS = ["title", "meta_description", "headings", "landmarks", "nav_links", "buttons",
          "aria_labels", "placeholders", "form_labels", "input_names", "card_texts",
          "url_tokens"]

# ---------------------------------------------------------------- prototypes
# RF001-C / RF2-C / D-SUP-01 이 쓴 frozen SSOT prototype 을 문자 그대로 재사용한다.
# 이 파일에서 문구를 바꾸지 않는다 (바꾸면 replication 이 아니다).
PROTO_SSOT_DEF = {
    "QUERY":
        "사용자가 검색 입력창에 자유 텍스트 질의를 입력하고 제출하여 검색 결과 목록 상태로 "
        "전환하는 것이 대표행동이다. 검색 입력 control, 검색 form, 검색 제출 버튼이 대표 "
        "표면이다. search box, search form, submit query, search results.",
    "CONTENT_OPEN":
        "이미 존재하는 기사, 영상, 콘텐츠 한 건을 목록에서 선택해 본문을 열거나 재생을 "
        "시작하는 것이 대표행동이다. 콘텐츠 카드 목록, 기사 본문, 미디어 재생이 대표 "
        "표면이다. article body, news, video playback, content card list.",
    "ITEM_DETAIL":
        "거래 대상 상품 한 건의 상세면에 들어가 상품명, 가격, 거래 control 의 존재를 확인하는 "
        "것이 대표행동이다. 반복되는 상품 카드 목록과 상품 상세 문서가 대표 표면이다. "
        "product name, price, cart, order, shopping mall, item detail page.",
    "PLACE_LOOKUP":
        "장소를 질의하거나 특정 장소의 상세면을 여는 것이 대표행동이다. 장소 검색 control, "
        "장소 목록, 지도, 주소, 장소 상세 패널이 대표 표면이다. map, place search, address, "
        "location, route, navigation.",
    "COMMUNICATION_ENTRY":
        "사람 사이의 게시물, 스레드, 메시지를 교환하는 공간에 진입하는 것이 대표행동이다. "
        "스레드 목록, 게시글 목록, 글쓰기 진입 control, 실제 로그인 gate 가 대표 표면이다. "
        "message, chat, post, thread, community, social feed, comment.",
    "FINANCIAL_ACTION_ENTRY":
        "금융처리 기능의 시작면을 열거나 그 기능을 시작하기 위해 필요한 실제 로그인 및 "
        "본인인증 gate 까지 진입하는 것이 대표행동이다. 잔액 조회, 이체, 송금, 결제, 카드, "
        "보험, 인증 기능 진입 control 이 대표 표면이다. bank, transfer, payment, balance, "
        "card, insurance, login, identity verification.",
    "UTILITY_ENTRY":
        "특정 목적의 도구 기능면을 열고 첫 primary control 을 사용할 수 있는 상태로 만드는 "
        "것이 대표행동이다. 단일 목적 기능 진입 control 과 그 기능 화면이 대표 표면이다. "
        "utility tool, service function, apply, reserve, issue, lookup, settings.",
}
PROTO_USER_BEHAVIOR = {
    "QUERY": "나는 궁금한 것을 검색창에 입력하고 검색 버튼을 눌러 결과 목록을 본다.",
    "CONTENT_OPEN": "나는 목록에서 기사나 영상 하나를 골라 눌러서 읽거나 본다.",
    "ITEM_DETAIL": "나는 사고 싶은 물건 하나를 눌러 상세 화면에서 가격과 정보를 확인한다.",
    "PLACE_LOOKUP": "나는 가려는 장소를 찾아보고 그 장소의 위치와 상세 정보를 확인한다.",
    "COMMUNICATION_ENTRY": "나는 다른 사람이 올린 글이나 메시지를 보러 대화 공간에 들어간다.",
    "FINANCIAL_ACTION_ENTRY": "나는 은행이나 카드 업무를 시작하려고 로그인 화면까지 들어간다.",
    "UTILITY_ENTRY": "나는 필요한 기능 하나를 열어서 바로 쓸 수 있는 상태까지 간다.",
}
PROTO_TERSE_LABEL = {
    "QUERY": "검색 질의 search query",
    "CONTENT_OPEN": "콘텐츠 열람 content open article video",
    "ITEM_DETAIL": "상품 상세 item detail product price",
    "PLACE_LOOKUP": "장소 조회 place lookup map location",
    "COMMUNICATION_ENTRY": "커뮤니케이션 진입 communication message post",
    "FINANCIAL_ACTION_ENTRY": "금융 기능 진입 financial action bank payment",
    "UTILITY_ENTRY": "도구 기능 진입 utility function tool",
}
PROTO_SETS = {"A_SSOT_DEF": PROTO_SSOT_DEF, "B_USER_BEHAVIOR": PROTO_USER_BEHAVIOR,
              "C_TERSE_LABEL": PROTO_TERSE_LABEL}
PRIMARY_PROTO = "A_SSOT_DEF"

MODELS = {
    "bge-m3": dict(hf="BAAI/bge-m3", batch=8, doc_prefix="", proto_prefix=""),
    # e5 규약: 비대칭 검색이면 문서 passage:, 질의 query:. prototype=query, page=passage 가 PRIMARY.
    "e5-small": dict(hf="intfloat/multilingual-e5-small", batch=32,
                     doc_prefix="passage: ", proto_prefix="query: "),
    "minilm": dict(hf="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                   batch=32, doc_prefix="", proto_prefix=""),
}
PRIMARY_MODEL = "bge-m3"

# ---------------------------------------------- EXP3 representation 정의 (RF2-C 원본)
REPRESENTATIONS = {
    "title": ["title"], "meta_description": ["meta_description"], "headings": ["headings"],
    "landmarks": ["landmarks"], "nav_links": ["nav_links"], "buttons": ["buttons"],
    "aria_labels": ["aria_labels"], "placeholders": ["placeholders"],
    "form_labels": ["form_labels"], "input_names": ["input_names"],
    "card_texts": ["card_texts"], "url_tokens": ["url_tokens"],
    "first_screen_interaction": ["buttons", "aria_labels", "placeholders"],
    "accessibility_text": ["aria_labels", "form_labels", "placeholders", "input_names"],
    "primary_controls": ["buttons", "aria_labels", "form_labels", "placeholders", "input_names"],
    "identity": ["title", "meta_description", "url_tokens"],
    "structure": ["title", "headings", "landmarks"],
    "content_body": ["headings", "card_texts"],
    "nav_surface": ["landmarks", "nav_links"],
    "ssot7_bundle": ["title", "headings", "landmarks", "aria_labels", "buttons",
                     "form_labels", "card_texts", "url_tokens"],
    "controls_plus_identity": ["title", "url_tokens", "buttons", "aria_labels",
                               "form_labels", "placeholders", "input_names"],
    "text_blob__ALL": FIELDS,
}
CTRL_FAMILY = ["buttons", "aria_labels", "placeholders", "form_labels", "input_names",
               "first_screen_interaction", "accessibility_text", "primary_controls"]
TOPIC_FAMILY = ["title", "meta_description", "headings", "landmarks", "nav_links",
                "card_texts", "url_tokens", "identity", "structure", "content_body",
                "nav_surface", "ssot7_bundle"]

# ---------------------------------------------- EXP4 (D-SUP-01) representation 정의
CTRL_FIELDS = ["buttons", "aria_labels", "placeholders", "form_labels", "input_names"]
TOPIC_FIELDS = ["title", "meta_description", "headings"]
URL_SYNTAX_TOKENS = ["https", "http", "www", "com", "co", "kr", "net", "org"]
DSUP_REPS = ["FULL", "CONTROL_ONLY", "TOPIC_ONLY", "NO_BRAND_DOMAIN"]
N_PLACEBO = 3

# ---------------------------------------------- EXP2 (RF001-B) brand vocabulary (원본 그대로)
BRAND_EXTRA = {
    "쿠팡", "쿠팡이츠", "카카오", "카카오톡", "카카오맵", "카카오t", "카카오모빌리티", "네이버", "네이버지도",
    "롯데", "롯데온", "롯데마트", "롯데백화점", "롯데홈쇼핑", "롯데하이마트", "하이마트", "신세계", "이마트",
    "이마트24", "현대", "현대카드", "현대백화점", "더현대", "삼성", "삼성카드", "삼성전자", "신한", "쏠", "sol",
    "하나", "하나은행", "국민", "국민은행", "kb", "kb페이", "kb스타뱅킹", "스타뱅킹", "농협", "nh", "콕뱅크",
    "홈플러스", "배민", "배달의민족", "우아한형제들", "토스", "지마켓", "g마켓", "티맵", "티맵모빌리티", "당근",
    "당근마켓", "컬리", "마켓컬리", "다이소", "세븐일레븐", "메가커피", "컴포즈", "컴포즈커피", "홈앤쇼핑",
    "넷플릭스", "유튜브", "구글", "크롬", "인스타그램", "틱톡", "밴드", "다음", "모니모", "캐시워크", "안랩",
    "에이닷", "sk텔레콤", "skt", "gs", "gs25", "지에스", "씨유", "cu", "미니스톱", "탑마트", "서원유통",
    "농협하나로마트", "하나로마트", "코스트코", "cj", "cj온스타일", "온스타일", "ns홈쇼핑", "11번가", "십일번가",
    "netflix", "youtube", "google", "chrome", "instagram", "tiktok", "kakao", "naver", "coupang",
    "coupangeats", "toss", "baemin", "kurly", "emart", "homeplus", "lotte", "shinsegae", "hyundai",
    "samsung", "shinhan", "hana", "kbstar", "kbcard", "nonghyup", "nhbank", "bgfretail", "gsretail",
    "daiso", "eleven", "ahnlab", "sktelecom", "band", "daangn", "11st", "gmarket", "cjonstyle",
    "hnsmall", "nsmall", "himart", "megacoffee", "composecoffee", "costco", "monimo", "cashwalk",
    "tmap", "tmapmobility", "seowon", "nhhanaro", "lottemart", "lotteon", "ellotte", "ehyundai",
    "thehyundaiseoul", "samsungsvc", "samsungcard", "hyundaicard", "daum", "lottehomeshopping",
    "kakaocorp", "navercorp", "kakaomobility", "lottemartzetta", "mplweb", "omoney", "mbiz",
    "zetta", "v3", "mycompany", "bank", "banking",
}
HOST_STOP = {"www", "com", "co", "kr", "net", "org", "im", "us", "http", "https", "m", "go", "or"}
TFIDF_LEGIT = ("A_blob_full", "B_title_head_nav", "C_blob_no_url", "D_deleak")
TFIDF_PRIMARY = "A_blob_full.word.logreg"
TFIDF_DELEAK_PRIMARY = "D_deleak.word.logreg"

GOOGLE_SERVICE = "Google"


# =============================================================== 기초 통계 도구
def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wilson(k: int, n: int, z: float = 1.959963985) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [float((c - h) / d), float((c + h) / d)]


def macro_f1_idx(pred: np.ndarray, true: np.ndarray, k: int = 7) -> float:
    fs = []
    for c in range(k):
        tp = int(np.sum((true == c) & (pred == c)))
        fp = int(np.sum((true != c) & (pred == c)))
        fn = int(np.sum((true == c) & (pred != c)))
        den = 2 * tp + fp + fn
        fs.append(2 * tp / den if den else 0.0)
    return float(np.mean(fs))


def macro_f1_batch_true(pred: np.ndarray, true_mat: np.ndarray, k: int = 7) -> np.ndarray:
    """pred 고정, true 가 (B,n) 행렬 (라벨 순열 귀무분포용). 벡터화."""
    out = np.zeros(true_mat.shape[0])
    for c in range(k):
        pc = (pred == c)
        tc = (true_mat == c)
        tp = (tc & pc).sum(1)
        fp = ((~tc) & pc).sum(1)
        fn = (tc & (~pc)).sum(1)
        den = 2 * tp + fp + fn
        out += np.where(den > 0, 2 * tp / np.maximum(den, 1), 0.0)
    return out / k


def macro_f1_batch_pred(pred_mat: np.ndarray, true: np.ndarray, k: int = 7) -> np.ndarray:
    """true 고정, pred 가 (B,n) 행렬 (stratified 무작위 예측기 분포용)."""
    out = np.zeros(pred_mat.shape[0])
    for c in range(k):
        tc = (true == c)
        pc = (pred_mat == c)
        tp = (pc & tc).sum(1)
        fp = (pc & (~tc)).sum(1)
        fn = ((~pc) & tc).sum(1)
        den = 2 * tp + fp + fn
        out += np.where(den > 0, 2 * tp / np.maximum(den, 1), 0.0)
    return out / k


# RF2-C 의 empty-field 정책: 해당 representation 이 빈 target 은 ABSTAIN(=7) 으로 두고
# 전체-56 분모에서 오답 처리한다. ABSTAIN 은 어떤 class 의 tp/fp 도 되지 않고 해당 true class 의
# fn 으로만 잡힌다. EXP3 는 RF2-C 재현이므로 이 정책을 그대로 쓴다.
KT_ABSTAIN = 7          # true class 수
KP_ABSTAIN = 8          # + ABSTAIN(=7) 예측 전용 class


def macro_f1_abstain(pred: np.ndarray, true: np.ndarray) -> float:
    cm = np.bincount(true * KP_ABSTAIN + pred,
                     minlength=KT_ABSTAIN * KP_ABSTAIN).reshape(KT_ABSTAIN, KP_ABSTAIN)
    tp = np.diag(cm[:, :KT_ABSTAIN]).astype(float)
    fp = cm[:, :KT_ABSTAIN].sum(0) - tp
    fn = cm.sum(1) - tp
    pr = np.where(tp + fp > 0, tp / np.maximum(tp + fp, 1e-12), 0.0)
    rc = np.where(tp + fn > 0, tp / np.maximum(tp + fn, 1e-12), 0.0)
    f = np.where(pr + rc > 0, 2 * pr * rc / np.maximum(pr + rc, 1e-12), 0.0)
    return float(f.mean())


def macro_f1_abstain_batch_true(pred: np.ndarray, true_mat: np.ndarray) -> np.ndarray:
    P, n = true_mat.shape
    idx = true_mat * KP_ABSTAIN + pred[None, :]
    off = (np.arange(P) * (KT_ABSTAIN * KP_ABSTAIN))[:, None]
    cm = np.bincount((idx + off).ravel(),
                     minlength=P * KT_ABSTAIN * KP_ABSTAIN).reshape(P, KT_ABSTAIN, KP_ABSTAIN)
    tp = np.einsum("pii->pi", cm[:, :, :KT_ABSTAIN]).astype(float)
    fp = cm[:, :, :KT_ABSTAIN].sum(1) - tp
    fn = cm.sum(2) - tp
    pr = np.where(tp + fp > 0, tp / np.maximum(tp + fp, 1e-12), 0.0)
    rc = np.where(tp + fn > 0, tp / np.maximum(tp + fn, 1e-12), 0.0)
    f = np.where(pr + rc > 0, 2 * pr * rc / np.maximum(pr + rc, 1e-12), 0.0)
    return f.mean(1)


def weighted_f1_idx(pred, true, k: int = 7) -> float:
    tot, acc = len(true), 0.0
    for c in range(k):
        sup = int(np.sum(true == c))
        if not sup:
            continue
        tp = int(np.sum((true == c) & (pred == c)))
        fp = int(np.sum((true != c) & (pred == c)))
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / sup
        acc += (2 * pr * rc / (pr + rc) if pr + rc else 0.0) * sup
    return float(acc / tot)


def pval_upper(null: np.ndarray, obs: float) -> float:
    return float((np.sum(null >= obs) + 1) / (len(null) + 1))


def cohen_kappa(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    labs = sorted(set(a.tolist()) | set(b.tolist()))
    n = len(a)
    po = float(np.mean(a == b))
    pe = sum((np.sum(a == l) / n) * (np.sum(b == l) / n) for l in labs)
    return float((po - pe) / (1 - pe)) if pe < 1 else float("nan")


def mcnemar_exact(a_correct: np.ndarray, b_correct: np.ndarray) -> dict:
    """정확 이항검정 (discordant pair)."""
    from math import comb
    b_a = int(np.sum(a_correct & ~b_correct))
    b_b = int(np.sum(~a_correct & b_correct))
    nd = b_a + b_b
    if nd == 0:
        return {"b_a_only": b_a, "b_b_only": b_b, "n_discordant": 0, "p_two_sided": 1.0}
    k = min(b_a, b_b)
    p = sum(comb(nd, i) for i in range(0, k + 1)) / (2 ** nd) * 2
    return {"b_a_only": b_a, "b_b_only": b_b, "n_discordant": nd,
            "p_two_sided": float(min(1.0, p))}


def per_class_report(pred: np.ndarray, true: np.ndarray) -> dict:
    out = {}
    for i, c in enumerate(ARCHETYPES):
        sup = int(np.sum(true == i))
        tp = int(np.sum((true == i) & (pred == i)))
        fp = int(np.sum((true != i) & (pred == i)))
        fn = sup - tp
        npred = tp + fp
        pr = tp / npred if npred else 0.0
        rc = tp / sup if sup else 0.0
        out[c] = {"support": sup, "n_predicted": npred, "tp": tp, "fp": fp, "fn": fn,
                  "recall": rc, "recall_fraction": f"{tp}/{sup}",
                  "recall_wilson95": wilson(tp, sup) if sup else [None, None],
                  "precision": pr, "precision_fraction": f"{tp}/{npred}" if npred else "0/0",
                  "precision_wilson95": wilson(tp, npred) if npred else [None, None],
                  "f1": (2 * pr * rc / (pr + rc)) if pr + rc else 0.0}
    return out


def summ(a: np.ndarray) -> dict:
    a = np.asarray(a, float)
    a = a[~np.isnan(a)]
    if a.size == 0:
        return {"n_folds": 0}
    return {"n_folds": int(a.size), "mean": float(a.mean()),
            "std": float(a.std(ddof=1)) if a.size > 1 else 0.0,
            "median": float(np.median(a)), "min": float(a.min()), "max": float(a.max()),
            "p2_5": float(np.percentile(a, 2.5)), "p97_5": float(np.percentile(a, 97.5))}


def bootstrap_ci(correct: np.ndarray, rng, n_boot: int = N_BOOT) -> list[float]:
    n = len(correct)
    idx = rng.integers(0, n, size=(n_boot, n))
    vals = correct[idx].mean(axis=1)
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def join_fields(row, fields) -> str:
    parts = [str(row[f]).strip() for f in fields if str(row.get(f, "")).strip()]
    return " \n ".join(parts)


# =============================================================== encoder (offline)
EMB_CACHE_DIR = Path(os.environ.get(
    "D15_EMB_CACHE",
    "/tmp/claude-1000/-home-sieg-projects-wsl-ProjectFinal/"
    "4ce53865-2c0b-4a99-b60a-11369195e644/scratchpad/d15_emb_cache"))


class EncodeCache:
    """모델별 text -> vector 캐시. v1/v2/v3 는 56행 중 4~11행만 다르므로 중복이 매우 크다.

    임베딩은 결정적(같은 모델·같은 문자열 → 같은 벡터)이므로 스크래치패드에 디스크 캐시를 둔다.
    캐시는 산출물이 아니라 재실행 비용을 줄이는 임시 파일이고, 저장소에는 들어가지 않는다.
    """

    def __init__(self):
        self.store: dict[str, dict[str, np.ndarray]] = {m: {} for m in MODELS}
        self.meta: dict[str, dict] = {}
        EMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        for m in MODELS:
            f = EMB_CACHE_DIR / f"{m}.npz"
            if f.exists():
                try:
                    z = np.load(f, allow_pickle=True)
                    keys = list(z["keys"])
                    vecs = z["vecs"]
                    self.store[m] = {str(k): vecs[i] for i, k in enumerate(keys)}
                    print(f"    [cache:{m}] loaded {len(self.store[m])} vectors from disk",
                          flush=True)
                except Exception as e:
                    print(f"    [cache:{m}] load failed ({e}) — 무시하고 새로 인코딩한다", flush=True)

    def _persist(self, model_key: str) -> None:
        d = self.store[model_key]
        if not d:
            return
        keys = list(d)
        np.savez_compressed(EMB_CACHE_DIR / f"{model_key}.npz",
                            keys=np.array(keys, dtype=object),
                            vecs=np.stack([d[k] for k in keys]))

    def encode(self, model_key: str, texts: list[str], prefix: str = "") -> np.ndarray:
        need = sorted({prefix + t for t in texts} - set(self.store[model_key]))
        if need:
            self._run(model_key, need)
        return np.stack([self.store[model_key][prefix + t] for t in texts])

    def _run(self, model_key: str, texts: list[str]) -> None:
        from sentence_transformers import SentenceTransformer
        import torch
        cfg = MODELS[model_key]
        t0 = time.time()
        torch.manual_seed(SEED)
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        m = SentenceTransformer(cfg["hf"], device=dev)
        if model_key not in self.meta:
            self.meta[model_key] = {"hf": cfg["hf"], "max_seq_length": int(m.max_seq_length),
                                    "dim": int(m.get_sentence_embedding_dimension()),
                                    "doc_prefix": cfg["doc_prefix"],
                                    "proto_prefix": cfg["proto_prefix"],
                                    "n_texts_encoded": 0, "n_truncated": 0}
        lens = [len(m.tokenizer(t, add_special_tokens=True)["input_ids"]) for t in texts]
        self.meta[model_key]["n_texts_encoded"] += len(texts)
        self.meta[model_key]["n_truncated"] += int(sum(1 for l in lens if l > m.max_seq_length))
        V = m.encode(texts, batch_size=cfg["batch"], normalize_embeddings=True,
                     convert_to_numpy=True, show_progress_bar=False).astype(np.float64)
        for t, v in zip(texts, V):
            self.store[model_key][t] = v
        self._persist(model_key)
        del m
        torch.cuda.empty_cache()
        print(f"    [encode:{model_key}] +{len(texts)} texts in {time.time() - t0:.1f}s "
              f"(cache={len(self.store[model_key])})", flush=True)


def zero_shot(doc_vecs: np.ndarray, proto_vecs: np.ndarray) -> dict:
    sims = doc_vecs @ proto_vecs.T
    order = np.argsort(-sims, axis=1)
    top1 = order[:, 0]
    marg = sims[np.arange(len(sims)), order[:, 0]] - sims[np.arange(len(sims)), order[:, 1]]
    return {"sims": sims, "top1": top1, "order": order, "margin": marg,
            "top1_sim": sims[np.arange(len(sims)), order[:, 0]]}


# =============================================================== 코퍼스 로딩/차이
def load_corpora() -> dict[str, pd.DataFrame]:
    out = {}
    for v, p in CORPUS_PATH.items():
        df = pd.read_csv(p, keep_default_na=False).fillna("")
        df = df[df["dom_found"] == 1].reset_index(drop=True)
        out[v] = df
    base = out["v3"]
    for v, df in out.items():
        assert list(df["wtg"]) == list(base["wtg"]), f"{v} wtg order mismatch"
        assert list(df["prior_archetype"]) == list(base["prior_archetype"])
    return out


def corpus_diff(dfs: dict[str, pd.DataFrame]) -> dict:
    out = {"n_rows": int(len(dfs["v3"])),
           "sha256": {v: sha256_file(CORPUS_PATH[v]) for v in VERSIONS},
           "blob_tokens_median": {v: float(dfs[v]["blob_tokens"].median()) for v in VERSIONS},
           "blob_tokens_mean": {v: float(dfs[v]["blob_tokens"].mean()) for v in VERSIONS},
           "pairs": {}}
    for a, b in (("v1", "v2"), ("v2", "v3"), ("v1", "v3")):
        A, B = dfs[a], dfs[b]
        per_field = {f: int((A[f].astype(str) != B[f].astype(str)).sum()) for f in FIELDS}
        chg = (A[FIELDS].astype(str) != B[FIELDS].astype(str)).any(axis=1)
        rows = []
        for i in np.where(chg.to_numpy())[0]:
            rows.append({"wtg": B.loc[i, "wtg"], "prior_service": B.loc[i, "prior_service"],
                         "prior_archetype": B.loc[i, "prior_archetype"],
                         "blob_tokens_before": int(A.loc[i, "blob_tokens"]),
                         "blob_tokens_after": int(B.loc[i, "blob_tokens"]),
                         "delta_tokens": int(B.loc[i, "blob_tokens"]) - int(A.loc[i, "blob_tokens"]),
                         "changed_fields": [f for f in FIELDS
                                            if str(A.loc[i, f]) != str(B.loc[i, f])]})
        out["pairs"][f"{a}->{b}"] = {"n_targets_changed": int(chg.sum()),
                                     "per_field_changed": per_field,
                                     "changed_targets": rows}
    return out


# =============================================================== 공통 baseline
def build_baselines(y_idx: np.ndarray, rng) -> dict:
    n = len(y_idx)
    classes, counts = np.unique(y_idx, return_counts=True)
    p = counts / counts.sum()
    pred_mat = rng.choice(classes, size=(N_MC, n), p=p)
    f1s = macro_f1_batch_pred(pred_mat, y_idx)
    accs = (pred_mat == y_idx).mean(axis=1)
    maj = int(classes[np.argmax(counts)])
    maj_pred = np.full(n, maj)
    return {
        "majority": {"rule": f"always {ARCHETYPES[maj]} (n={int(counts.max())}/{n})",
                     "prior_agreement": float(np.mean(maj_pred == y_idx)),
                     "macro_f1": macro_f1_idx(maj_pred, y_idx),
                     "note": "majority 는 6/7 class 에서 recall 0 이라 macro F1 lift 의 판정 기준선이 될 수 없다. 참고용."},
        "stratified": {"n_draws": N_MC,
                       "macro_f1_mean": float(f1s.mean()), "macro_f1_sd": float(f1s.std(ddof=1)),
                       "macro_f1_p95": float(np.percentile(f1s, 95)),
                       "macro_f1_ci95": [float(np.percentile(f1s, 2.5)),
                                         float(np.percentile(f1s, 97.5))],
                       "prior_agreement_mean": float(accs.mean()),
                       "prior_agreement_p95": float(np.percentile(accs, 95)),
                       "rule": "관측 class marginal 무작위 예측기. 판정 기준선(JUDGMENT BASELINE)."},
        "_f1_null": f1s, "_acc_null": accs,
    }


def perm_null_labels(y_idx: np.ndarray, pred: np.ndarray, rng, strata=None,
                     abstain: bool = False) -> dict:
    n = len(y_idx)
    if strata is None:
        perm = np.argsort(rng.random((N_MC, n)), axis=1)
        true_mat = y_idx[perm]
    else:
        true_mat = np.tile(y_idx, (N_MC, 1))
        for s in np.unique(strata):
            idx = np.where(strata == s)[0]
            order = np.argsort(rng.random((N_MC, len(idx))), axis=1)
            true_mat[:, idx] = y_idx[idx][order]
    f1s = (macro_f1_abstain_batch_true(pred, true_mat) if abstain
           else macro_f1_batch_true(pred, true_mat))
    accs = (true_mat == pred).mean(axis=1)
    return {"f1": f1s, "acc": accs}


# =============================================================== EXP1
def exp1_embedding(dfs, cache, splits, y_idx, rng) -> dict:
    """RF001-C 계열 재현 — bge-m3/e5/minilm × prototype A/B/C × text_blob."""
    print("[EXP1] embedding prototype", flush=True)
    n = len(y_idx)
    res = {"design": {
        "replicates": "RF001-C (D-RF-001-C)",
        "representation": "text_blob (코퍼스 빌더 정본 결합)",
        "models": {k: v["hf"] for k, v in MODELS.items()},
        "prototype_sets": list(PROTO_SETS),
        "primary_config": f"{PRIMARY_MODEL}|{PRIMARY_PROTO}",
        "target_variable": "prior_archetype (gold label 아님) → 지표는 prior_agreement = 업종 배정 재현율",
        "judgment_baseline": "stratified (MC 20000). majority 대비 lift 는 병기만.",
        "verdict_rule": ("RF001-C 원본 규칙 그대로: beats & n_beat>=7 & no flip & length-survives "
                         "→ SUPPORTED; n_beat>=5 & survives → PARTIALLY_SUPPORTED; n_beat==0 → "
                         "NOT_SUPPORTED; 그 외 beats 면 PARTIALLY_SUPPORTED, 아니면 INCONCLUSIVE"),
    }, "per_version": {}}

    for v in VERSIONS:
        df = dfs[v]
        docs = df["text_blob"].astype(str).tolist()
        toks = df["blob_tokens"].to_numpy(float)
        base = build_baselines(y_idx, np.random.default_rng(SEED))
        f1null, accnull = base.pop("_f1_null"), base.pop("_acc_null")
        strat = base["stratified"]

        configs, preds = {}, {}
        for mname, cfg in MODELS.items():
            D = cache.encode(mname, docs, prefix=cfg["doc_prefix"])
            for sname, pset in PROTO_SETS.items():
                P = cache.encode(mname, [pset[a] for a in ARCHETYPES], prefix=cfg["proto_prefix"])
                r = zero_shot(D, P)
                key = f"{mname}|{sname}"
                preds[key] = r
                f1 = macro_f1_idx(r["top1"], y_idx)
                correct = r["top1"] == y_idx
                acc = float(correct.mean())
                k = int(correct.sum())
                pn = perm_null_labels(y_idx, r["top1"], np.random.default_rng(SEED + 1))
                fold = np.array([macro_f1_idx(r["top1"][te], y_idx[te]) for _, te in splits])
                configs[key] = {
                    "model": mname, "prototype_set": sname,
                    "prior_agreement": acc, "prior_agreement_fraction": f"{k}/{n}",
                    "prior_agreement_wilson95": wilson(k, n),
                    "prior_agreement_bootstrap95": bootstrap_ci(correct, np.random.default_rng(SEED + 7)),
                    "macro_f1": f1, "weighted_f1": weighted_f1_idx(r["top1"], y_idx),
                    "top2_prior_agreement": float(np.mean([y_idx[i] in r["order"][i, :2]
                                                           for i in range(n)])),
                    "n_distinct_predicted_classes": int(len(set(r["top1"].tolist()))),
                    "predicted_class_counts": {a: int(np.sum(r["top1"] == i))
                                               for i, a in enumerate(ARCHETYPES)},
                    "margin_median": float(np.median(r["margin"])),
                    "margin_p10": float(np.percentile(r["margin"], 10)),
                    "margin_p90": float(np.percentile(r["margin"], 90)),
                    "fold_macro_f1_30": {"scores": fold.tolist(), "summary": summ(fold)},
                    "label_permutation_test": {"macro_f1_p": pval_upper(pn["f1"], f1),
                                               "prior_agreement_p": pval_upper(pn["acc"], acc),
                                               "macro_f1_null_mean": float(pn["f1"].mean()),
                                               "macro_f1_null_p95": float(np.percentile(pn["f1"], 95)),
                                               "n_permutations": N_MC},
                    "vs_stratified": {
                        "macro_f1_delta": f1 - strat["macro_f1_mean"],
                        "macro_f1_p_vs_stratified_predictor": pval_upper(f1null, f1),
                        "prior_agreement_delta": acc - strat["prior_agreement_mean"],
                        "prior_agreement_p_vs_stratified_predictor": pval_upper(accnull, acc)},
                    "beats_judgment_baseline": bool(f1 > strat["macro_f1_p95"]),
                }

        # e5 prefix 규약 ablation (대칭 변형)
        e5alt = {}
        Dq = cache.encode("e5-small", docs, prefix="query: ")
        for sname, pset in PROTO_SETS.items():
            Pq = cache.encode("e5-small", [pset[a] for a in ARCHETYPES], prefix="query: ")
            r = zero_shot(Dq, Pq)
            f1 = macro_f1_idx(r["top1"], y_idx)
            e5alt[f"e5-small-symmetric|{sname}"] = {
                "macro_f1": f1, "prior_agreement": float(np.mean(r["top1"] == y_idx)),
                "delta_macro_f1_vs_asymmetric": f1 - configs[f"e5-small|{sname}"]["macro_f1"]}

        # prototype 민감도
        proto_sens = {"per_model": {}, "pairwise_kappa": {}}
        for mname in MODELS:
            f1s = {s: configs[f"{mname}|{s}"]["macro_f1"] for s in PROTO_SETS}
            accs_ = {s: configs[f"{mname}|{s}"]["prior_agreement"] for s in PROTO_SETS}
            beats = {s: configs[f"{mname}|{s}"]["beats_judgment_baseline"] for s in PROTO_SETS}
            proto_sens["per_model"][mname] = {
                "macro_f1_by_set": f1s,
                "macro_f1_range": max(f1s.values()) - min(f1s.values()),
                "prior_agreement_by_set": accs_,
                "prior_agreement_range": max(accs_.values()) - min(accs_.values()),
                "beats_stratified_p95_by_set": beats,
                "verdict_flips_across_sets": len(set(beats.values())) > 1}
            sl = list(PROTO_SETS)
            for i, s1 in enumerate(sl):
                for s2 in sl[i + 1:]:
                    proto_sens["pairwise_kappa"][f"{mname}|{s1}~{s2}"] = {
                        "cohen_kappa": cohen_kappa(preds[f"{mname}|{s1}"]["top1"],
                                                   preds[f"{mname}|{s2}"]["top1"]),
                        "raw_prediction_agreement": float(np.mean(
                            preds[f"{mname}|{s1}"]["top1"] == preds[f"{mname}|{s2}"]["top1"]))}
        allf1 = [configs[k]["macro_f1"] for k in configs]
        proto_sens["global"] = {
            "macro_f1_min": min(allf1), "macro_f1_max": max(allf1),
            "macro_f1_range_all_9_configs": max(allf1) - min(allf1),
            "n_configs_beating_stratified_p95": int(sum(configs[k]["beats_judgment_baseline"]
                                                        for k in configs)),
            "n_configs": len(configs),
            "any_verdict_flip": any(proto_sens["per_model"][m]["verdict_flips_across_sets"]
                                    for m in MODELS)}

        # 길이 교란 (PRIMARY 만) — 길이 tertile 내 순열
        pkey = f"{PRIMARY_MODEL}|{PRIMARY_PROTO}"
        tert = np.asarray(pd.qcut(pd.Series(toks), 3,
                                  labels=["T1_short", "T2_mid", "T3_long"],
                                  duplicates="drop").astype(str))
        pn_len = perm_null_labels(y_idx, preds[pkey]["top1"],
                                  np.random.default_rng(SEED + 2), strata=tert)
        f1p = configs[pkey]["macro_f1"]
        surv = bool(f1p > np.percentile(pn_len["f1"], 95))
        # 길이만 쓰는 LOO nearest-class-mean
        lt = np.log1p(toks)
        loo = []
        for i in range(n):
            m = np.ones(n, bool); m[i] = False
            best, bd = None, np.inf
            for c in range(7):
                sel = m & (y_idx == c)
                if not sel.any():
                    continue
                d = abs(lt[i] - lt[sel].mean())
                if d < bd:
                    bd, best = d, c
            loo.append(best)
        loo = np.array(loo)
        length_tests = {
            "length_stratified_permutation_primary": {
                "macro_f1_p": pval_upper(pn_len["f1"], f1p),
                "macro_f1_null_p95": float(np.percentile(pn_len["f1"], 95)),
                "signal_survives_length_control": surv,
                "n_permutations": N_MC,
                "note": "길이 tertile 안에서만 라벨을 섞어 길이-라벨 연관을 보존한 귀무분포"},
            "length_only_classifier_loo": {
                "rule": "LOO nearest-class-mean on log1p(blob_tokens)",
                "prior_agreement": float(np.mean(loo == y_idx)),
                "macro_f1": macro_f1_idx(loo, y_idx),
                "beats_stratified_p95": bool(macro_f1_idx(loo, y_idx) > strat["macro_f1_p95"])},
        }

        # 판정 (RF001-C 원본 규칙)
        beats = configs[pkey]["beats_judgment_baseline"]
        n_beat = proto_sens["global"]["n_configs_beating_stratified_p95"]
        flip = proto_sens["global"]["any_verdict_flip"]
        if beats and n_beat >= 7 and not flip and surv:
            verdict = "SUPPORTED"
        elif n_beat >= 5 and surv:
            verdict = "PARTIALLY_SUPPORTED"
        elif n_beat == 0:
            verdict = "NOT_SUPPORTED"
        else:
            verdict = "PARTIALLY_SUPPORTED" if beats else "INCONCLUSIVE"
        h_null = "REFUTED" if n_beat >= 5 else ("NOT_SUPPORTED" if n_beat == 0 else "INCONCLUSIVE")
        h_len = ("NOT_SUPPORTED" if surv and
                 length_tests["length_only_classifier_loo"]["macro_f1"] <= strat["macro_f1_p95"]
                 else ("SUPPORTED" if not surv else "PARTIALLY_SUPPORTED"))
        h_proto = ("SUPPORTED" if flip
                   else ("PARTIALLY_SUPPORTED"
                         if proto_sens["global"]["macro_f1_range_all_9_configs"] >= 0.10
                         else "NOT_SUPPORTED"))

        res["per_version"][v] = {
            "verdict": verdict,
            "hypothesis_verdicts": {
                "H-RF001-C-EMBED-PROTOTYPE": verdict,
                "H-C-null (baseline 과 무차이)": h_null,
                "H-C-length (길이/도메인 어휘밀도를 재는 중)": h_len,
                "H-C-prototype (문구 민감)": h_proto},
            "baselines": base, "configs": configs,
            "primary": {"config": pkey, **configs[pkey],
                        "per_class": per_class_report(preds[pkey]["top1"], y_idx),
                        "confusion_matrix": {
                            "rows_true": ARCHETYPES, "cols_pred": ARCHETYPES,
                            "matrix": [[int(np.sum((y_idx == a) & (preds[pkey]["top1"] == b)))
                                        for b in range(7)] for a in range(7)]}},
            "e5_prefix_ablation": e5alt,
            "prototype_sensitivity": proto_sens,
            "length_confound": length_tests,
            "_primary_pred": preds[pkey]["top1"].tolist(),
            "_all_preds": {k: preds[k]["top1"].tolist() for k in preds},
        }
        print(f"  [EXP1:{v}] verdict={verdict} primary macroF1="
              f"{configs[pkey]['macro_f1']:.4f} agree={configs[pkey]['prior_agreement_fraction']}",
              flush=True)
    return res


# =============================================================== EXP2
def build_brand_terms(df: pd.DataFrame) -> list[str]:
    terms: set[str] = set(BRAND_EXTRA)
    for s in df["prior_service"].fillna(""):
        s = str(s).strip()
        if len(s) >= 2:
            terms.add(s.lower())
        for p in re.split(r"[\s/·\-]+", s):
            if len(p) >= 2:
                terms.add(p.lower())
    for u in df["prior_url"].fillna(""):
        host = urlparse(str(u)).hostname or ""
        for t in re.split(r"[.\-]", host):
            if t and t not in HOST_STOP and len(t) >= 2:
                terms.add(t.lower())
    return sorted(terms, key=len, reverse=True)


def make_featuresets(df: pd.DataFrame, pat: re.Pattern) -> dict[str, list[str]]:
    blob_full = df["text_blob"].astype(str).tolist()
    thn = [" \n ".join(x for x in (str(r.get("title") or ""), str(r.get("headings") or ""),
                                   str(r.get("nav_links") or "")) if x)
           for _, r in df.iterrows()]
    no_url = [" \n ".join(str(r[f]) for f in FIELDS if f != "url_tokens" and str(r[f]).strip())
              for _, r in df.iterrows()]
    deleak = [re.sub(r"\s+", " ", pat.sub(" ", t)).strip() for t in no_url]
    brand_only = [" ".join(m.group(0).lower() for m in pat.finditer(t)) for t in blob_full]
    return {"A_blob_full": blob_full, "B_title_head_nav": thn, "C_blob_no_url": no_url,
            "D_deleak": deleak, "E_brand_only": brand_only}


def _make_vec(analyzer: str):
    from sklearn.feature_extraction.text import TfidfVectorizer
    if analyzer == "word":
        return TfidfVectorizer(analyzer="word", ngram_range=(1, 2), lowercase=True,
                               token_pattern=r"(?u)\b\w{2,}\b", min_df=1, sublinear_tf=True)
    return TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), lowercase=True,
                           min_df=2, sublinear_tf=True)


def _make_clf(model: str):
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    if model == "logreg":
        return LogisticRegression(max_iter=5000, C=1.0, class_weight="balanced", random_state=SEED)
    return LinearSVC(C=1.0, class_weight="balanced", random_state=SEED, max_iter=20000)


def _fit_fold(X, y, tr, te, vec_kind, model_kind):
    from sklearn.pipeline import Pipeline
    from sklearn.metrics import f1_score
    try:
        pipe = Pipeline([("v", _make_vec(vec_kind)), ("c", _make_clf(model_kind))])
        pipe.fit(X[tr], y[tr])
        pred = pipe.predict(X[te])
        return float(f1_score(y[te], pred, average="macro", zero_division=0)), list(pred), 0
    except Exception:
        return np.nan, [], 1


def exp2_tfidf(dfs, splits, y_str, splits3) -> dict:
    """RF001-B 계열 재현 — TF-IDF 20셀 격자 + 브랜드-only 대조군 E."""
    from joblib import Parallel, delayed
    from sklearn.dummy import DummyClassifier
    from sklearn.metrics import f1_score
    print("[EXP2] tfidf", flush=True)
    n = len(y_str)
    res = {"design": {
        "replicates": "RF001-B (D-RF-001-B)",
        "cv": "RepeatedStratifiedKFold(n_splits=3, n_repeats=10, random_state=20260827)",
        "n_folds": len(splits),
        "pre_declared_primary": TFIDF_PRIMARY,
        "pre_declared_deleak_primary": TFIDF_DELEAK_PRIMARY,
        "featureset_definitions": {
            "A_blob_full": "text_blob 전체(=url_tokens 포함)",
            "B_title_head_nav": "title + headings + nav_links 만",
            "C_blob_no_url": "text_blob 구성 필드 중 url_tokens 제외",
            "D_deleak": "C_blob_no_url 에서 브랜드/서비스명 문자열 전면 제거",
            "E_brand_only": "text_blob 에서 브랜드/서비스명 토큰만 남김 (leak 상한 대조군, 모델 후보 아님)"},
        "judgment_basis": ("fold macro F1 의 p2_5 가 stratified baseline 평균보다 위면 '분리된다'. "
                           "판정은 사전 선언 primary 와 E 를 제외한 사후 최댓값 둘 다로 한다."),
        "grid_size": 20,
    }, "per_version": {}}

    for v in VERSIONS:
        df = dfs[v]
        brand_terms = build_brand_terms(df)
        pat = re.compile("|".join(re.escape(t) for t in brand_terms), re.IGNORECASE)
        fsets = make_featuresets(df, pat)
        tokstats = {}
        for k, docs in fsets.items():
            toks = [len(TOK.findall(d)) for d in docs]
            tokstats[k] = {"n_docs": len(docs), "empty_docs": int(sum(1 for t in toks if t == 0)),
                           "tokens_median": float(np.median(toks)), "tokens_min": int(min(toks)),
                           "tokens_max": int(max(toks)), "tokens_mean": float(np.mean(toks))}

        # baselines
        base = {}
        Xz = np.zeros((n, 1))
        for strat in ("most_frequent", "stratified"):
            sc = []
            for tr, te in splits:
                d = DummyClassifier(strategy=strat, random_state=SEED)
                d.fit(Xz[tr], y_str[tr])
                sc.append(f1_score(y_str[te], d.predict(Xz[te]), average="macro", zero_division=0))
            base[strat] = {"fold_scores": sc, "summary": summ(np.array(sc))}
        strat_mean = base["stratified"]["summary"]["mean"]
        mf_mean = base["most_frequent"]["summary"]["mean"]

        jobs, keys = [], []
        for fs_name, docs in fsets.items():
            X = np.array(docs, dtype=object)
            for vk in ("word", "char_wb"):
                for mk in ("logreg", "linsvc"):
                    for tr, te in splits:
                        jobs.append(delayed(_fit_fold)(X, y_str, tr, te, vk, mk))
                        keys.append(f"{fs_name}.{vk}.{mk}")
        t0 = time.time()
        outs = Parallel(n_jobs=8, backend="loky", verbose=0)(jobs)
        print(f"  [EXP2:{v}] grid {len(jobs)} fits in {time.time() - t0:.0f}s", flush=True)

        configs, oof = {}, {}
        for key, (f1, pred, fail) in zip(keys, outs):
            configs.setdefault(key, {"fold_scores": [], "fold_failures": 0})
            configs[key]["fold_scores"].append(f1)
            configs[key]["fold_failures"] += fail
            oof.setdefault(key, []).append(pred)
        for key, c in configs.items():
            fs, vk, mk = key.split(".")
            arr = np.array(c["fold_scores"], float)
            s = summ(arr)
            c.update({"featureset": fs, "analyzer": vk, "model": mk, "summary": s,
                      "lift_vs_stratified": float(s["mean"] - strat_mean),
                      "lift_vs_most_frequent": float(s["mean"] - mf_mean),
                      "ci_includes_stratified_mean": bool(s["p2_5"] <= strat_mean <= s["p97_5"]),
                      "separates_from_stratified": bool(s["p2_5"] > strat_mean)})

        legit_keys = [k for k in configs if configs[k]["featureset"] in TFIDF_LEGIT]
        best_key = max(legit_keys, key=lambda k: configs[k]["summary"]["mean"])
        best_any_key = max(configs, key=lambda k: configs[k]["summary"]["mean"])
        brand_keys = [k for k in configs if configs[k]["featureset"] == "E_brand_only"]
        brand_only_separates = any(configs[k]["separates_from_stratified"] for k in brand_keys)

        # 브랜드 leak 지표
        m = lambda k: configs[k]["summary"]["mean"]
        deleak_sep = configs[TFIDF_DELEAK_PRIMARY]["separates_from_stratified"]
        leak = {
            "primary_full_macro_f1": m(TFIDF_PRIMARY),
            "primary_deleak_macro_f1": m(TFIDF_DELEAK_PRIMARY),
            "deleak_drop_abs": m(TFIDF_PRIMARY) - m(TFIDF_DELEAK_PRIMARY),
            "deleak_retention_frac": (m(TFIDF_DELEAK_PRIMARY) / m(TFIDF_PRIMARY)
                                      if m(TFIDF_PRIMARY) else None),
            "brand_only_macro_f1_word_logreg": m("E_brand_only.word.logreg"),
            "brand_only_best_macro_f1": max(m(k) for k in brand_keys),
            "brand_only_best_key": max(brand_keys, key=m),
            "brand_only_vs_stratified_lift": m("E_brand_only.word.logreg") - strat_mean,
            "deleak_still_above_stratified": deleak_sep,
            "n_brand_terms_removed": len(brand_terms),
        }

        # permutation (사전 선언 4 config)
        perm_targets = {"primary": TFIDF_PRIMARY, "deleak": TFIDF_DELEAK_PRIMARY,
                        "best_legit_text": best_key, "brand_only_control": best_any_key
                        if configs[best_any_key]["featureset"] == "E_brand_only"
                        else max(brand_keys, key=m)}
        perms = {}
        rngp = np.random.default_rng(SEED + 31)
        for label, key in perm_targets.items():
            fs, vk, mk = key.split(".")
            X = np.array(fsets[fs], dtype=object)
            obs_folds = [_fit_fold(X, y_str, tr, te, vk, mk)[0] for tr, te in splits3]
            obs = float(np.nanmean(obs_folds))
            perm_y = [rngp.permutation(y_str) for _ in range(N_PERM_TFIDF)]
            t0 = time.time()
            null_scores = Parallel(n_jobs=8, backend="loky")(
                delayed(_perm_score)(X, yp, splits3, vk, mk) for yp in perm_y)
            null = np.array(null_scores, float)
            perms[label] = {"config": key, "cv": "StratifiedKFold(3, shuffle, seed)",
                            "score": obs, "n_permutations": N_PERM_TFIDF,
                            "p_value": float((np.sum(null >= obs) + 1) / (N_PERM_TFIDF + 1)),
                            "null_mean": float(null.mean()),
                            "null_p97_5": float(np.percentile(null, 97.5))}
            print(f"  [EXP2:{v}] perm {label}={key} p={perms[label]['p_value']:.4f} "
                  f"({time.time() - t0:.0f}s)", flush=True)

        primary_beats = configs[TFIDF_PRIMARY]["separates_from_stratified"]
        beats = configs[best_key]["separates_from_stratified"]
        if primary_beats and beats:
            verdict = "SUPPORTED"
        elif beats and not primary_beats:
            verdict = "PARTIALLY_SUPPORTED"
        else:
            verdict = "NOT_SUPPORTED"
        h_null = "REFUTED" if beats else "SUPPORTED"
        if brand_only_separates and not deleak_sep:
            h_leak = "SUPPORTED"
        elif deleak_sep and leak["deleak_retention_frac"] and leak["deleak_retention_frac"] > 0.7:
            h_leak = "NOT_SUPPORTED"
        elif not beats and not brand_only_separates:
            h_leak = "NOT_TESTABLE"
        else:
            h_leak = "PARTIALLY_SUPPORTED"

        # per-class (사전 선언 primary, OOF 다수결)
        pc_pred = _oof_majority(oof[TFIDF_PRIMARY], splits, n)

        res["per_version"][v] = {
            "verdict": verdict,
            "hypothesis_verdicts": {"H-RF001-B-TFIDF": verdict, "H-B-null": h_null,
                                    "H-B-leak": h_leak},
            "featureset_token_stats": tokstats,
            "baselines": base,
            "configs": {k: {kk: vv for kk, vv in c.items() if kk != "fold_scores"} |
                        {"fold_scores": c["fold_scores"]} for k, c in configs.items()},
            "primary_result": configs[TFIDF_PRIMARY],
            "deleak_primary_result": configs[TFIDF_DELEAK_PRIMARY],
            "best_config_post_hoc": {"key": best_key, **configs[best_key],
                                     "scope": "featureset A/B/C/D 16셀 중 최댓값 (E 대조군 제외)",
                                     "caveat": "16셀 최댓값이므로 selection bias 가 있다."},
            "best_config_including_control": {
                "key": best_any_key, "mean": m(best_any_key),
                "is_brand_only_control": configs[best_any_key]["featureset"] == "E_brand_only"},
            "judgment": {"stratified_baseline_mean": strat_mean,
                         "most_frequent_baseline_mean": mf_mean,
                         "primary_separates": primary_beats, "best_legit_separates": beats,
                         "brand_only_control_separates": brand_only_separates,
                         "deleak_separates": deleak_sep},
            "permutation_test": perms,
            "brand_leak_test": leak,
            "per_class_oof_majority_primary": per_class_report(
                np.array([A2I[p] for p in pc_pred]), np.array([A2I[t] for t in y_str])),
            "_oof_primary_pred": pc_pred,
        }
        print(f"  [EXP2:{v}] verdict={verdict} primary={m(TFIDF_PRIMARY):.4f} "
              f"best_legit={best_key}:{m(best_key):.4f} brandE={leak['brand_only_best_macro_f1']:.4f}",
              flush=True)
    return res


def _perm_score(X, yp, splits3, vk, mk) -> float:
    sc = [_fit_fold(X, yp, tr, te, vk, mk)[0] for tr, te in splits3]
    return float(np.nanmean(sc))


def _oof_majority(pred_lists, splits, n) -> list[str]:
    votes = [Counter() for _ in range(n)]
    for (tr, te), preds in zip(splits, pred_lists):
        if not preds:
            continue
        for j, idx in enumerate(te):
            votes[idx][preds[j]] += 1
    return [v.most_common(1)[0][0] if v else ARCHETYPES[0] for v in votes]


# =============================================================== EXP3
def exp3_field_ablation(dfs, cache, splits, y_idx) -> dict:
    """RF2-C 계열 재현 — 22 representation × prototype A/B/C, bge-m3."""
    print("[EXP3] field ablation", flush=True)
    n = len(y_idx)
    res = {"design": {
        "replicates": "RF2-C (D-RF-002-C)",
        "model": MODELS[PRIMARY_MODEL]["hf"], "primary_prototype_set": PRIMARY_PROTO,
        "n_representations": len(REPRESENTATIONS),
        "prototype_policy": "모든 representation 에 동일한 frozen 세트. field 별 문구 변경 없음.",
        "empty_field_policy": ("RF2-C 원본과 동일: 빈 representation 은 ABSTAIN 으로 두고 "
                               "전체-56 분모에서 오답 처리한다. ABSTAIN 은 어떤 class 의 tp/fp 도 "
                               "되지 않고 해당 true class 의 fn 으로만 잡힌다."),
        "hypothesis_rules": {
            "H-C1": "text_blob__ALL 이 최선인가. 다른 representation 이 이기면 REFUTED.",
            "H-C2": ("control-family(buttons/aria/placeholder/label/input name 및 그 조합) 최댓값이 "
                     "topic/identity-family 최댓값보다 크면 SUPPORTED, text_blob__ALL 보다만 크면 "
                     "PARTIALLY_SUPPORTED, 둘 다 아니면 NOT_SUPPORTED"),
            "H-C3": "representation 간 macro F1 범위가 prototype 세트 간 최대 범위보다 작으면 SUPPORTED",
        },
        "control_family": CTRL_FAMILY, "topic_family": TOPIC_FAMILY,
        "representation_fields": REPRESENTATIONS,
    }, "per_version": {}}

    for v in VERSIONS:
        df = dfs[v]
        base = build_baselines(y_idx, np.random.default_rng(SEED))
        base.pop("_f1_null"); base.pop("_acc_null")
        strat = base["stratified"]
        texts = {rep: [join_fields(r, fl) for _, r in df.iterrows()]
                 for rep, fl in REPRESENTATIONS.items()}
        grid, preds = {}, {}
        # RF2-C 의 empty-field 정책을 그대로 쓴다: 빈 representation 은 인코딩하지 않고
        # ABSTAIN(=7) 으로 두며, 전체-56 분모에서 오답으로 센다. ABSTAIN 은 어떤 class 의
        # tp/fp 도 되지 않는다. (이 정책을 빼면 title 처럼 빈 값이 있는 field 의 macro F1 이
        # RF2-C 와 어긋난다 — 실제로 그것이 이 replication 초기 실행의 불일치 원인이었다.)
        for sname, pset in PROTO_SETS.items():
            P = cache.encode(PRIMARY_MODEL, [pset[a] for a in ARCHETYPES])
            for rep, tl in texts.items():
                empty = np.array([not t.strip() for t in tl])
                enc_idx = np.where(~empty)[0]
                D = np.zeros((n, P.shape[1]), dtype=np.float64)
                if len(enc_idx):
                    D[enc_idx] = cache.encode(PRIMARY_MODEL, [tl[i] for i in enc_idx])
                r = zero_shot(D, P)
                yhat = np.where(empty, KT_ABSTAIN, r["top1"]).astype(int)
                key = f"{rep}|{sname}"
                preds[key] = yhat
                f1 = macro_f1_abstain(yhat, y_idx)
                correct = yhat == y_idx
                k = int(correct.sum())
                toks = np.array([len(TOK.findall(t)) for t in tl])
                nonempty = ~empty
                pn = perm_null_labels(y_idx, yhat, np.random.default_rng(SEED + 3),
                                      abstain=True)
                fold = np.array([macro_f1_abstain(yhat[te], y_idx[te]) for _, te in splits])
                grid[key] = {
                    "representation": rep, "prototype_set": sname, "macro_f1": f1,
                    "prior_agreement_all56": float(correct.mean()),
                    "n_agree_all56": k, "prior_agreement_all56_wilson95": wilson(k, n),
                    "prior_agreement_nonempty": (float(correct[nonempty].mean())
                                                 if nonempty.any() else None),
                    "n_nonempty": int(nonempty.sum()), "n_empty": int(empty.sum()),
                    "margin_median": float(np.median(r["margin"][nonempty]))
                                     if nonempty.any() else None,
                    "tokens_median": float(np.median(toks)),
                    "perm_p_macro_f1": pval_upper(pn["f1"], f1),
                    "beats_stratified_p95": bool(f1 > strat["macro_f1_p95"]),
                    "fold_macro_f1_30": summ(fold),
                    "n_abstain": int(empty.sum()),
                    "n_distinct_predicted_classes": int(len(set(yhat[nonempty].tolist()))),
                }
        prim = {rep: grid[f"{rep}|{PRIMARY_PROTO}"] for rep in REPRESENTATIONS}
        ranking = sorted(prim.values(), key=lambda d: -d["macro_f1"])
        proto_stab = {}
        for rep in REPRESENTATIONS:
            f1s = {s: grid[f"{rep}|{s}"]["macro_f1"] for s in PROTO_SETS}
            beats = {s: grid[f"{rep}|{s}"]["beats_stratified_p95"] for s in PROTO_SETS}
            proto_stab[rep] = {"macro_f1_by_set": f1s,
                               "macro_f1_range": max(f1s.values()) - min(f1s.values()),
                               "verdict_flip_vs_stratified_p95": len(set(beats.values())) > 1}
        max_proto_range = max(d["macro_f1_range"] for d in proto_stab.values())
        field_range = max(d["macro_f1"] for d in prim.values()) - min(d["macro_f1"] for d in prim.values())

        best_ctrl = max(CTRL_FAMILY, key=lambda r_: prim[r_]["macro_f1"])
        best_topic = max(TOPIC_FAMILY, key=lambda r_: prim[r_]["macro_f1"])
        blob_f1 = prim["text_blob__ALL"]["macro_f1"]
        best_overall = ranking[0]["representation"]

        h_c1 = "REFUTED" if best_overall != "text_blob__ALL" else "SUPPORTED"
        if prim[best_ctrl]["macro_f1"] > prim[best_topic]["macro_f1"]:
            h_c2 = "SUPPORTED"
        elif prim[best_ctrl]["macro_f1"] > blob_f1:
            h_c2 = "PARTIALLY_SUPPORTED"
        else:
            h_c2 = "NOT_SUPPORTED"
        h_c3 = "SUPPORTED" if field_range < max_proto_range else "REFUTED"
        verdict = ("PARTIALLY_SUPPORTED" if (h_c1 == "REFUTED" and h_c2 == "NOT_SUPPORTED"
                                             and h_c3 == "REFUTED")
                   else ("SUPPORTED" if h_c2 == "SUPPORTED" else "PARTIALLY_SUPPORTED"))

        res["per_version"][v] = {
            "verdict": verdict,
            "hypotheses": {"H-C1 text_blob 전체가 최선": h_c1,
                           "H-C2 primary controls·accessibility text 가 더 informative": h_c2,
                           "H-C3 field 간 차이가 prototype 노이즈보다 작다": h_c3},
            "baselines": base,
            "field_ranking_primary": ranking,
            "grid": grid,
            "prototype_stability": proto_stab,
            "headline": {"best_representation": best_overall,
                         "best_macro_f1": ranking[0]["macro_f1"],
                         "best_prior_agreement_all56": ranking[0]["prior_agreement_all56"],
                         "text_blob_macro_f1": blob_f1,
                         "text_blob_prior_agreement_all56": prim["text_blob__ALL"]["prior_agreement_all56"],
                         "best_control_surface": best_ctrl,
                         "best_control_macro_f1": prim[best_ctrl]["macro_f1"],
                         "best_topic_surface": best_topic,
                         "best_topic_macro_f1": prim[best_topic]["macro_f1"],
                         "primary_controls_macro_f1": prim["primary_controls"]["macro_f1"],
                         "title_macro_f1": prim["title"]["macro_f1"],
                         "field_macro_f1_range": field_range,
                         "max_prototype_macro_f1_range": max_proto_range,
                         "stratified_p95_macro_f1": strat["macro_f1_p95"]},
            "_preds": {k: preds[k].tolist() for k in preds},
        }
        print(f"  [EXP3:{v}] verdict={verdict} rank1={best_overall}:{ranking[0]['macro_f1']:.4f} "
              f"blob={blob_f1:.4f} best_ctrl={best_ctrl}:{prim[best_ctrl]['macro_f1']:.4f} "
              f"H-C2={h_c2}", flush=True)
    return res


# =============================================================== EXP4
def brand_domain_tokens(row, alias) -> list[str]:
    toks: set[str] = set()
    svc = str(row.get("prior_service", "") or "")
    for t in TOK.findall(svc):
        if len(t) >= 2:
            toks.add(t.lower())
    compact = re.sub(r"\s+", "", svc)
    if len(compact) >= 2:
        toks.add(compact.lower())
    host = (urlparse(str(row.get("prior_url", "") or "")).hostname or "").lower()
    for lab in re.split(r"[.\-]", host):
        if len(lab) >= 2:
            toks.add(lab)
    toks.update(URL_SYNTAX_TOKENS)
    if alias:
        for t in TOK.findall(str(alias)):
            if len(t) >= 2:
                toks.add(t.lower())
    return sorted(toks, key=lambda s: (-len(s), s))


def strip_brand(text: str, toks: list[str]) -> tuple[str, Counter]:
    removed: Counter = Counter()
    out = text
    for t in toks:
        if HANGUL.search(t):
            pat = re.compile(re.escape(t), re.IGNORECASE)
        else:
            pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.IGNORECASE)
        out, cnt = pat.subn(" ", out)
        if cnt:
            removed[t] = cnt
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in out.split("\n")]
    return " \n ".join(ln for ln in lines if ln), removed


def placebo_strip(text: str, blacklist: list[str], n_remove: int, r) -> str:
    spans = [m.span() for m in TOK.finditer(text)]
    toks = [text[a:b].lower() for a, b in spans]
    bl = set(blacklist)
    bl_h = [t for t in bl if HANGUL.search(t)]
    elig = [i for i, t in enumerate(toks) if t not in bl and not any(h in t for h in bl_h)]
    k = min(int(n_remove), len(elig))
    chosen = set(r.choice(elig, size=k, replace=False).tolist()) if k else set()
    out, last = [], 0
    for i, (a, b) in enumerate(spans):
        if i in chosen:
            out.append(text[last:a]); out.append(" "); last = b
    out.append(text[last:])
    s2 = "".join(out)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s2.split("\n")]
    return " \n ".join(ln for ln in lines if ln)


def exp4_representation(dfs, cache, splits, y_idx, alias_map) -> dict:
    """D-SUP-01 계열 재현 — FULL/CONTROL_ONLY/TOPIC_ONLY/NO_BRAND_DOMAIN. prior-free 헤드라인."""
    print("[EXP4] representation ablation", flush=True)
    n = len(y_idx)
    res = {"design": {
        "replicates": "D-SUP-01",
        "headline_metric": "prior 를 쓰지 않는 representation 간 예측 일치율 + McNemar exact",
        "prior_based_route": "NOT_TESTABLE — D-FACT-01 전단사 때문에 prior 기반 지표는 두 가설을 구분하지 못한다",
        "representations": DSUP_REPS,
        "analysis_set": "complete_case (4개 representation 모두 토큰>=2 인 target)",
        "control_fields": CTRL_FIELDS, "topic_fields": TOPIC_FIELDS,
        "n_placebo_replicates": N_PLACEBO,
    }, "per_version": {}}

    for v in VERSIONS:
        df = dfs[v]
        texts = {"FULL": [str(t) for t in df["text_blob"]],
                 "CONTROL_ONLY": [join_fields(r, CTRL_FIELDS) for _, r in df.iterrows()],
                 "TOPIC_ONLY": [join_fields(r, TOPIC_FIELDS) for _, r in df.iterrows()]}
        nb, audit = [], []
        for i, r in df.iterrows():
            toks = brand_domain_tokens(r, alias_map.get(r["wtg"]))
            stripped, removed = strip_brand(texts["FULL"][i], toks)
            nb.append(stripped)
            audit.append({"wtg": r["wtg"], "blacklist_tokens": toks,
                          "tokens_before": len(TOK.findall(texts["FULL"][i])),
                          "tokens_after": len(TOK.findall(stripped)),
                          "n_removed_occurrences": int(sum(removed.values()))})
        texts["NO_BRAND_DOMAIN"] = nb
        prng = np.random.default_rng(SEED + 101)
        for rep_i in range(N_PLACEBO):
            texts[f"_PLACEBO_{rep_i + 1}"] = [
                placebo_strip(texts["FULL"][i], audit[i]["blacklist_tokens"],
                              audit[i]["tokens_before"] - audit[i]["tokens_after"], prng)
                for i in range(n)]

        tokcount = {k: np.array([len(TOK.findall(t)) for t in val]) for k, val in texts.items()}
        complete = np.ones(n, bool)
        for rep in DSUP_REPS:
            complete &= tokcount[rep] >= 2
        idx_cc = np.where(complete)[0]

        base = build_baselines(y_idx[idx_cc], np.random.default_rng(SEED))
        base.pop("_f1_null"); base.pop("_acc_null")

        top1 = {}
        for sname, pset in PROTO_SETS.items():
            P = cache.encode(PRIMARY_MODEL, [pset[a] for a in ARCHETYPES])
            for rep, tl in texts.items():
                D = cache.encode(PRIMARY_MODEL, tl)
                r = zero_shot(D, P)
                top1[(rep, sname)] = r
        # --- prior-free 헤드라인 E1: 어느 표면이 FULL 의 예측을 재현하는가
        E1, E2, E3, E5 = {}, {}, {}, {}
        for sname in PROTO_SETS:
            full = top1[("FULL", sname)]["top1"][idx_cc]
            top = top1[("TOPIC_ONLY", sname)]["top1"][idx_cc]
            ctl = top1[("CONTROL_ONLY", sname)]["top1"][idx_cc]
            a_ok, b_ok = (top == full), (ctl == full)
            mc = mcnemar_exact(a_ok, b_ok)
            m_ = len(idx_cc)
            E1[sname] = {
                "n": m_,
                "topic_reproduces_full": float(a_ok.mean()),
                "topic_reproduces_full_fraction": f"{int(a_ok.sum())}/{m_}",
                "topic_reproduces_full_wilson95": wilson(int(a_ok.sum()), m_),
                "control_reproduces_full": float(b_ok.mean()),
                "control_reproduces_full_fraction": f"{int(b_ok.sum())}/{m_}",
                "control_reproduces_full_wilson95": wilson(int(b_ok.sum()), m_),
                "difference_topic_minus_control": float(a_ok.mean() - b_ok.mean()),
                "mcnemar_exact": mc}
            nbp = top1[("NO_BRAND_DOMAIN", sname)]["top1"][idx_cc]
            ch_brand = int(np.sum(nbp != full))
            ch_plac = [int(np.sum(top1[(f"_PLACEBO_{i + 1}", sname)]["top1"][idx_cc] != full))
                       for i in range(N_PLACEBO)]
            E2[sname] = {
                "n": m_, "brand_removal_pred_change": ch_brand / m_,
                "brand_removal_pred_change_fraction": f"{ch_brand}/{m_}",
                "brand_removal_pred_change_wilson95": wilson(ch_brand, m_),
                "placebo_pred_change_by_replicate": [c / m_ for c in ch_plac],
                "placebo_pred_change_mean": float(np.mean(ch_plac) / m_),
                "placebo_pred_change_min": float(min(ch_plac) / m_),
                "placebo_pred_change_max": float(max(ch_plac) / m_),
                "brand_exceeds_placebo_max": bool(ch_brand > max(ch_plac)),
                "brand_within_placebo_range": bool(min(ch_plac) <= ch_brand <= max(ch_plac))}
            E3[sname] = {"top1_agreement": float(np.mean(ctl == top)),
                         "cohen_kappa": cohen_kappa(ctl, top)}
            E5[sname] = {rep: float(np.median(top1[(rep, sname)]["margin"][idx_cc]))
                         for rep in DSUP_REPS}

        ps = PRIMARY_PROTO
        # 진단용 prior 기반 지표(헤드라인 아님)
        diag = {}
        for rep in DSUP_REPS:
            p = top1[(rep, ps)]["top1"][idx_cc]
            t = y_idx[idx_cc]
            fold = np.array([macro_f1_idx(top1[(rep, ps)]["top1"][te], y_idx[te])
                             for _, te in splits])
            diag[rep] = {"macro_f1_complete_case": macro_f1_idx(p, t),
                         "prior_agreement_complete_case": float(np.mean(p == t)),
                         "n_distinct_predicted_classes": int(len(set(p.tolist()))),
                         "fold_macro_f1_30_all56": summ(fold),
                         "note": "prior 기반 지표는 전단사 때문에 판정 근거가 아니라 진단이다."}

        topic_gt = (E1[ps]["difference_topic_minus_control"] > 0
                    and E1[ps]["mcnemar_exact"]["p_two_sided"] < 0.05)
        ctrl_gt = (E1[ps]["difference_topic_minus_control"] < 0
                   and E1[ps]["mcnemar_exact"]["p_two_sided"] < 0.05)
        h_interaction = "REFUTED" if topic_gt else ("SUPPORTED" if ctrl_gt else "INCONCLUSIVE")
        h_topic_limb = "SUPPORTED" if topic_gt else "NOT_SUPPORTED"
        h_brand_limb = "REFUTED" if E2[ps]["brand_within_placebo_range"] else "SUPPORTED"
        h_domain = ("PARTIALLY_SUPPORTED" if (h_topic_limb == "SUPPORTED" and h_brand_limb == "REFUTED")
                    else ("SUPPORTED" if (h_topic_limb == "SUPPORTED" and h_brand_limb == "SUPPORTED")
                          else "NOT_SUPPORTED"))
        h_both = "NOT_SUPPORTED" if (topic_gt or ctrl_gt) else "PARTIALLY_SUPPORTED"
        h_insep = "SUPPORTED"
        verdict = "PARTIALLY_SUPPORTED" if h_domain in ("PARTIALLY_SUPPORTED", "SUPPORTED") else "INCONCLUSIVE"

        res["per_version"][v] = {
            "verdict": verdict,
            "verdict_basis": ("prior 를 쓰지 않는 행동 비교(E1/E2). prior 기반 경로는 D-FACT-01 전단사로 "
                              "NOT_TESTABLE."),
            "prior_based_route_verdict": "NOT_TESTABLE",
            "hypothesis_verdicts_priorfree": {
                "H-SUP01-INTERACTION": h_interaction,
                "H-SUP01-DOMAIN": h_domain,
                "H-SUP01-DOMAIN::brand_token_limb": h_brand_limb,
                "H-SUP01-DOMAIN::topic_vocabulary_limb": h_topic_limb,
                "H-SUP01-BOTH": h_both,
                "H-SUP01-INSEPARABLE": h_insep},
            "n_complete_case": int(len(idx_cc)),
            "baselines_complete_case": base,
            "E1_which_surface_drives_FULL": E1,
            "E1_token_mass_confound_check": {
                "topic_tokens_median": float(np.median(tokcount["TOPIC_ONLY"][idx_cc])),
                "control_tokens_median": float(np.median(tokcount["CONTROL_ONLY"][idx_cc])),
                "control_not_smaller_than_topic": bool(
                    np.median(tokcount["CONTROL_ONLY"][idx_cc])
                    >= np.median(tokcount["TOPIC_ONLY"][idx_cc]))},
            "E2_brand_removal_vs_placebo": E2,
            "E3_control_vs_topic_agreement": E3,
            "E5_margin_median_by_representation": E5,
            "prior_based_diagnostics": diag,
            "_preds": {f"{rep}|{s}": top1[(rep, s)]["top1"].tolist()
                       for rep in DSUP_REPS for s in PROTO_SETS},
            "_idx_complete_case": idx_cc.tolist(),
        }
        print(f"  [EXP4:{v}] verdict={verdict} topic={E1[ps]['topic_reproduces_full']:.2f} "
              f"control={E1[ps]['control_reproduces_full']:.2f} "
              f"mcnemar_p={E1[ps]['mcnemar_exact']['p_two_sided']:.4g} "
              f"brand={E2[ps]['brand_removal_pred_change']:.2f} "
              f"placebo={E2[ps]['placebo_pred_change_min']:.2f}~{E2[ps]['placebo_pred_change_max']:.2f}",
              flush=True)
    return res


# =============================================================== Google / QUERY
def google_query_section(dfs, e1, e2, e3, e4, y_idx, google_i) -> dict:
    g = {"why": ("v2→v3 에서 Google 의 text_blob 토큰이 118→57 (-52%) 로 줄었다. QUERY 는 n=4 뿐이라 "
                 "한 target 의 예측 변화가 class recall 을 0.25 단위로 움직인다. 별도로 본다."),
         "target": {}, "prediction_by_experiment": {}, "query_class_metrics": {}}
    for v in VERSIONS:
        df = dfs[v]
        g["target"][v] = {"wtg": df.loc[google_i, "wtg"],
                          "prior_service": df.loc[google_i, "prior_service"],
                          "prior_archetype": df.loc[google_i, "prior_archetype"],
                          "blob_tokens": int(df.loc[google_i, "blob_tokens"]),
                          "blob_chars": int(df.loc[google_i, "blob_chars"]),
                          "landmarks_len": len(str(df.loc[google_i, "landmarks"])),
                          "buttons_len": len(str(df.loc[google_i, "buttons"])),
                          "landmarks_preview": str(df.loc[google_i, "landmarks"])[:200],
                          "buttons_preview": str(df.loc[google_i, "buttons"])[:200]}
    # EXP1 primary
    g["prediction_by_experiment"]["EXP1_embedding_primary"] = {
        v: ARCHETYPES[e1["per_version"][v]["_primary_pred"][google_i]] for v in VERSIONS}
    g["prediction_by_experiment"]["EXP1_all_9_configs"] = {
        v: {k: ARCHETYPES[p[google_i]] for k, p in e1["per_version"][v]["_all_preds"].items()}
        for v in VERSIONS}
    g["prediction_by_experiment"]["EXP2_tfidf_oof_majority_primary"] = {
        v: e2["per_version"][v]["_oof_primary_pred"][google_i] for v in VERSIONS}
    _lab = lambda c: ARCHETYPES[c] if c < len(ARCHETYPES) else "ABSTAIN"
    g["prediction_by_experiment"]["EXP3_selected_representations"] = {
        v: {rep: _lab(e3["per_version"][v]["_preds"][f"{rep}|{PRIMARY_PROTO}"][google_i])
            for rep in ("title", "identity", "primary_controls", "text_blob__ALL")}
        for v in VERSIONS}
    g["prediction_by_experiment"]["EXP4_representations"] = {
        v: {rep: ARCHETYPES[e4["per_version"][v]["_preds"][f"{rep}|{PRIMARY_PROTO}"][google_i]]
            for rep in DSUP_REPS} for v in VERSIONS}
    # QUERY class metrics
    for v in VERSIONS:
        pc1 = e1["per_version"][v]["primary"]["per_class"]["QUERY"]
        pc2 = e2["per_version"][v]["per_class_oof_majority_primary"]["QUERY"]
        blob = np.array(e3["per_version"][v]["_preds"][f"text_blob__ALL|{PRIMARY_PROTO}"])
        ttl = np.array(e3["per_version"][v]["_preds"][f"title|{PRIMARY_PROTO}"])
        # ABSTAIN(=7) 은 어떤 class 의 예측도 아니다 → per-class 집계에서 predicted 로 세지 않는다.
        g["query_class_metrics"][v] = {
            "EXP1_embedding_primary": {k: pc1[k] for k in
                                       ("support", "tp", "fp", "fn", "recall", "recall_fraction",
                                        "recall_wilson95", "precision", "precision_fraction", "f1")},
            "EXP2_tfidf_oof_majority": {k: pc2[k] for k in
                                        ("support", "tp", "fp", "fn", "recall", "recall_fraction",
                                         "recall_wilson95", "precision", "precision_fraction", "f1")},
            "EXP3_text_blob__ALL": per_class_report(blob, y_idx)["QUERY"],
            "EXP3_title": per_class_report(ttl, y_idx)["QUERY"],
        }
    g["google_prediction_changed_v2_to_v3"] = {
        exp: (d["v2"] != d["v3"]) for exp, d in g["prediction_by_experiment"].items()
        if isinstance(d.get("v2"), str)}
    return g


# =============================================================== noise vs delta
def noise_analysis(e1, e2, e3, e4, y_idx, diff) -> dict:
    n = len(y_idx)
    out = {"why": ("v2→v3 에서 바뀐 target 이 4/56 뿐이므로 prior_agreement 는 원리적으로 최대 "
                   "4/56=0.0714 만 움직일 수 있다. 지표가 안 움직이는 것도 결과다."),
           "max_possible_prior_agreement_shift_v2_v3": 4 / n,
           "max_possible_prior_agreement_shift_v1_v3": 11 / n,
           "per_experiment": {}}
    # EXP1 primary
    p = {v: np.array(e1["per_version"][v]["_primary_pred"]) for v in VERSIONS}
    f1 = {v: e1["per_version"][v]["primary"]["macro_f1"] for v in VERSIONS}
    fold_sd = {v: e1["per_version"][v]["primary"]["fold_macro_f1_30"]["summary"]["std"]
               for v in VERSIONS}
    proto_range = {v: e1["per_version"][v]["prototype_sensitivity"]["per_model"][PRIMARY_MODEL]["macro_f1_range"]
                   for v in VERSIONS}
    out["per_experiment"]["EXP1_embedding_primary"] = {
        "macro_f1": f1,
        "delta_v2_v3": f1["v3"] - f1["v2"], "delta_v1_v3": f1["v3"] - f1["v1"],
        "fold_macro_f1_sd_v3": fold_sd["v3"], "prototype_set_range_v3": proto_range["v3"],
        "delta_v2_v3_exceeds_fold_sd": abs(f1["v3"] - f1["v2"]) > fold_sd["v3"],
        "delta_v1_v3_exceeds_fold_sd": abs(f1["v3"] - f1["v1"]) > fold_sd["v3"],
        "delta_v2_v3_exceeds_prototype_range": abs(f1["v3"] - f1["v2"]) > proto_range["v3"],
        "n_targets_prediction_changed_v2_v3": int(np.sum(p["v2"] != p["v3"])),
        "n_targets_prediction_changed_v1_v3": int(np.sum(p["v1"] != p["v3"])),
        "mcnemar_correctness_v2_vs_v3": mcnemar_exact(p["v2"] == y_idx, p["v3"] == y_idx),
        "mcnemar_correctness_v1_vs_v3": mcnemar_exact(p["v1"] == y_idx, p["v3"] == y_idx),
    }
    # EXP2 primary
    m2 = {v: e2["per_version"][v]["primary_result"]["summary"]["mean"] for v in VERSIONS}
    sd2 = {v: e2["per_version"][v]["primary_result"]["summary"]["std"] for v in VERSIONS}
    b2 = {v: e2["per_version"][v]["brand_leak_test"]["brand_only_best_macro_f1"] for v in VERSIONS}
    out["per_experiment"]["EXP2_tfidf_primary"] = {
        "macro_f1_mean_30folds": m2, "fold_sd": sd2,
        "delta_v2_v3": m2["v3"] - m2["v2"], "delta_v1_v3": m2["v3"] - m2["v1"],
        "delta_v2_v3_exceeds_fold_sd": abs(m2["v3"] - m2["v2"]) > sd2["v3"],
        "delta_v1_v3_exceeds_fold_sd": abs(m2["v3"] - m2["v1"]) > sd2["v3"],
        "brand_only_control_macro_f1": b2,
    }
    # EXP3
    for rep in ("title", "identity", "primary_controls", "text_blob__ALL"):
        vals = {v: e3["per_version"][v]["grid"][f"{rep}|{PRIMARY_PROTO}"]["macro_f1"] for v in VERSIONS}
        sd = {v: e3["per_version"][v]["grid"][f"{rep}|{PRIMARY_PROTO}"]["fold_macro_f1_30"]["std"]
              for v in VERSIONS}
        pr = {v: e3["per_version"][v]["prototype_stability"][rep]["macro_f1_range"] for v in VERSIONS}
        pred = {v: np.array(e3["per_version"][v]["_preds"][f"{rep}|{PRIMARY_PROTO}"]) for v in VERSIONS}
        out["per_experiment"][f"EXP3_{rep}"] = {
            "macro_f1": vals, "fold_sd_v3": sd["v3"], "prototype_set_range_v3": pr["v3"],
            "delta_v2_v3": vals["v3"] - vals["v2"], "delta_v1_v3": vals["v3"] - vals["v1"],
            "delta_v2_v3_exceeds_fold_sd": abs(vals["v3"] - vals["v2"]) > sd["v3"],
            "delta_v2_v3_exceeds_prototype_range": abs(vals["v3"] - vals["v2"]) > pr["v3"],
            "n_targets_prediction_changed_v2_v3": int(np.sum(pred["v2"] != pred["v3"])),
            "mcnemar_correctness_v2_vs_v3": mcnemar_exact(pred["v2"] == y_idx, pred["v3"] == y_idx)}
    # EXP4
    tt = {v: e4["per_version"][v]["E1_which_surface_drives_FULL"][PRIMARY_PROTO] for v in VERSIONS}
    out["per_experiment"]["EXP4_E1_topic_minus_control"] = {
        "topic_reproduces_full": {v: tt[v]["topic_reproduces_full"] for v in VERSIONS},
        "control_reproduces_full": {v: tt[v]["control_reproduces_full"] for v in VERSIONS},
        "difference": {v: tt[v]["difference_topic_minus_control"] for v in VERSIONS},
        "mcnemar_p": {v: tt[v]["mcnemar_exact"]["p_two_sided"] for v in VERSIONS},
        "n_complete_case": {v: e4["per_version"][v]["n_complete_case"] for v in VERSIONS}}
    return out


# =============================================================== figures
def make_figures(doc) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["DejaVu Sans"]
    FIGDIR.mkdir(parents=True, exist_ok=True)
    figs = {}
    VC = {"SUPPORTED": 4, "PARTIALLY_SUPPORTED": 3, "INCONCLUSIVE": 2, "NOT_SUPPORTED": 1,
          "REFUTED": 0, "NOT_TESTABLE": 2}

    # 1) verdict grid
    grid = doc["verdict_grid"]["rows"]
    # matplotlib 기본 폰트(DejaVu Sans)에는 한글 글리프가 없어 라벨이 tofu 로 찍힌다.
    # 시스템 한글 폰트에 의존하지 않도록 그림 라벨만 ASCII 로 줄인다.
    # (판정 값 자체는 원문 그대로이고, 한글 전문은 JSON 과 FINDINGS 표에 있다.)
    ASCII_ROW = {
        "EXP1 H-C-null (baseline 과 무차이)": "EXP1 H-C-null (no diff vs baseline)",
        "EXP1 H-C-length (길이/도메인 어휘밀도를 재는 중)": "EXP1 H-C-length (measuring length/vocab density)",
        "EXP1 H-C-prototype (문구 민감)": "EXP1 H-C-prototype (wording sensitive)",
        "EXP3 H-C1 text_blob 전체가 최선": "EXP3 H-C1 (full text_blob is best)",
        "EXP3 H-C2 primary controls·accessibility text 가 더 informative":
            "EXP3 H-C2 (controls/a11y text more informative)",
        "EXP3 H-C3 field 간 차이가 prototype 노이즈보다 작다":
            "EXP3 H-C3 (field gap < prototype noise)",
    }
    labels = [ASCII_ROW.get(g["row"], g["row"]) for g in grid]
    M = np.array([[VC.get(g[v], 2) for v in VERSIONS] for g in grid], float)
    fig, ax = plt.subplots(figsize=(7.2, 0.42 * len(labels) + 1.8))
    im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=4, aspect="auto")
    ax.set_xticks(range(3), [v + "\n" + doc["corpus_diff"]["sha256"][v][:7] for v in VERSIONS])
    ax.set_yticks(range(len(labels)), labels, fontsize=7)
    for i in range(len(labels)):
        for j, v in enumerate(VERSIONS):
            txt = grid[i][v].replace("PARTIALLY_SUPPORTED", "PARTIAL").replace("NOT_SUPPORTED", "NOT_SUP")
            ax.text(j, i, txt, ha="center", va="center", fontsize=6.5)
    changed = [i for i, g in enumerate(grid) if g["changed_v2_to_v3"]]
    for i in changed:
        ax.add_patch(plt.Rectangle((-0.5, i - 0.5), 3, 1, fill=False, edgecolor="blue", lw=2))
    ax.set_title("RQ-D15 verdict grid: 4 experiments x corpus v1/v2/v3\n"
                 "(blue box = verdict changed v2->v3)", fontsize=9)
    fig.tight_layout()
    p = FIGDIR / "RQ_D15_verdict_grid.png"
    fig.savefig(p, dpi=140); plt.close(fig)
    figs["verdict_grid"] = str(p)

    # 2) headline metrics across versions
    fig, ax = plt.subplots(1, 4, figsize=(15, 3.6))
    e1 = doc["exp1_embedding"]["per_version"]
    x = np.arange(3)
    ax[0].bar(x - 0.2, [e1[v]["primary"]["macro_f1"] for v in VERSIONS], 0.4, label="macro F1")
    ax[0].bar(x + 0.2, [e1[v]["primary"]["prior_agreement"] for v in VERSIONS], 0.4,
              label="prior_agreement")
    ax[0].axhline(e1["v3"]["baselines"]["stratified"]["macro_f1_p95"], ls="--", c="r", lw=1,
                  label="strat p95 F1")
    ax[0].set_title("EXP1 embedding PRIMARY\nbge-m3 | A_SSOT_DEF | text_blob", fontsize=8)
    e2 = doc["exp2_tfidf"]["per_version"]
    ax[1].bar(x - 0.2, [e2[v]["primary_result"]["summary"]["mean"] for v in VERSIONS], 0.4,
              yerr=[e2[v]["primary_result"]["summary"]["std"] for v in VERSIONS],
              label="primary A.word.logreg", capsize=3)
    ax[1].bar(x + 0.2, [e2[v]["brand_leak_test"]["brand_only_best_macro_f1"] for v in VERSIONS], 0.4,
              label="E_brand_only best", color="tab:orange")
    ax[1].axhline(e2["v3"]["judgment"]["stratified_baseline_mean"], ls="--", c="r", lw=1,
                  label="stratified mean")
    ax[1].set_title("EXP2 TF-IDF (30 folds)", fontsize=8)
    e3 = doc["exp3_field_ablation"]["per_version"]
    for rep, c in (("title", "tab:blue"), ("identity", "tab:green"),
                   ("text_blob__ALL", "tab:purple"), ("primary_controls", "tab:red")):
        ax[2].plot(x, [e3[v]["grid"][f"{rep}|{PRIMARY_PROTO}"]["macro_f1"] for v in VERSIONS],
                   "o-", label=rep, color=c)
    ax[2].axhline(e3["v3"]["baselines"]["stratified"]["macro_f1_p95"], ls="--", c="r", lw=1)
    ax[2].set_title("EXP3 field ablation (macro F1)", fontsize=8)
    e4 = doc["exp4_representation_ablation"]["per_version"]
    ax[3].plot(x, [e4[v]["E1_which_surface_drives_FULL"][PRIMARY_PROTO]["topic_reproduces_full"]
                   for v in VERSIONS], "o-", label="TOPIC reproduces FULL")
    ax[3].plot(x, [e4[v]["E1_which_surface_drives_FULL"][PRIMARY_PROTO]["control_reproduces_full"]
                   for v in VERSIONS], "s-", label="CONTROL reproduces FULL")
    ax[3].set_title("EXP4 prior-free E1", fontsize=8)
    for a in ax:
        a.set_xticks(x, VERSIONS); a.grid(alpha=.3); a.legend(fontsize=6); a.set_ylim(0, 1)
    fig.tight_layout()
    p = FIGDIR / "RQ_D15_headline_metrics.png"
    fig.savefig(p, dpi=140); plt.close(fig)
    figs["headline_metrics"] = str(p)

    # 3) Google / QUERY
    gq = doc["google_and_query"]
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    ax[0].bar(x, [gq["target"][v]["blob_tokens"] for v in VERSIONS], color="tab:gray")
    for i, v in enumerate(VERSIONS):
        ax[0].text(i, gq["target"][v]["blob_tokens"] + 2, str(gq["target"][v]["blob_tokens"]),
                   ha="center", fontsize=8)
    ax[0].set_title("Google target blob_tokens", fontsize=9)
    preds = gq["prediction_by_experiment"]["EXP1_all_9_configs"]
    cfgs = list(preds["v3"])
    Mx = np.array([[ARCHETYPES.index(preds[v][c]) for v in VERSIONS] for c in cfgs], float)
    ax[1].imshow(Mx, cmap="tab10", vmin=0, vmax=9, aspect="auto")
    ax[1].set_yticks(range(len(cfgs)), cfgs, fontsize=6)
    ax[1].set_xticks(range(3), VERSIONS)
    for i in range(len(cfgs)):
        for j, v in enumerate(VERSIONS):
            ax[1].text(j, i, preds[v][cfgs[i]][:10], ha="center", va="center", fontsize=5.5)
    ax[1].set_title("Google predicted class (EXP1, 9 configs)\ntrue prior = QUERY", fontsize=8)
    qm = doc["google_and_query"]["query_class_metrics"]
    w = 0.25
    for k, (src, off) in enumerate((("EXP1_embedding_primary", -w), ("EXP3_text_blob__ALL", 0),
                                    ("EXP3_title", w))):
        ax[2].bar(x + off, [qm[v][src]["recall"] for v in VERSIONS], w, label=src)
    ax[2].set_xticks(x, VERSIONS); ax[2].set_ylim(0, 1.05); ax[2].legend(fontsize=6)
    ax[2].set_title("QUERY class recall (n=4)", fontsize=9)
    for a in (ax[0], ax[2]):
        a.grid(alpha=.3, axis="y")
    fig.tight_layout()
    p = FIGDIR / "RQ_D15_google_query.png"
    fig.savefig(p, dpi=140); plt.close(fig)
    figs["google_query"] = str(p)

    # 4) fold distributions + permutation nulls
    fig, ax = plt.subplots(1, 3, figsize=(13.5, 3.8))
    for v in VERSIONS:
        ax[0].hist(e1[v]["primary"]["fold_macro_f1_30"]["scores"], bins=12, alpha=.45, label=f"{v}")
    ax[0].set_title("EXP1 primary: macro F1 over 30 test folds", fontsize=9)
    for v in VERSIONS:
        ax[1].hist(e2[v]["primary_result"]["fold_scores"], bins=12, alpha=.45, label=v)
    ax[1].axvline(e2["v3"]["judgment"]["stratified_baseline_mean"], ls="--", c="r",
                  label="stratified mean")
    ax[1].set_title("EXP2 primary: macro F1 over 30 CV folds", fontsize=9)
    keys = ["EXP1 perm p", "EXP2 primary perm p", "EXP2 brand-only perm p"]
    vals = {v: [e1[v]["primary"]["label_permutation_test"]["macro_f1_p"],
                e2[v]["permutation_test"]["primary"]["p_value"],
                e2[v]["permutation_test"]["brand_only_control"]["p_value"]] for v in VERSIONS}
    for i, v in enumerate(VERSIONS):
        ax[2].bar(np.arange(3) + (i - 1) * 0.27, vals[v], 0.27, label=v)
    ax[2].axhline(0.05, ls="--", c="r", lw=1)
    ax[2].set_yscale("log"); ax[2].set_xticks(range(3), keys, fontsize=7)
    ax[2].set_title("permutation p-values", fontsize=9)
    for a in ax:
        a.legend(fontsize=6); a.grid(alpha=.3)
    fig.tight_layout()
    p = FIGDIR / "RQ_D15_uncertainty.png"
    fig.savefig(p, dpi=140); plt.close(fig)
    figs["uncertainty"] = str(p)
    return figs


# =============================================================== main
def main() -> int:
    t_start = time.time()
    rng = np.random.default_rng(SEED)
    dfs = load_corpora()
    base = dfs["v3"]
    n = len(base)
    y_str = base["prior_archetype"].to_numpy()
    y_idx = np.array([A2I[a] for a in y_str])
    google_i = int(np.where(base["prior_service"].astype(str) == GOOGLE_SERVICE)[0][0])

    d14 = json.loads(INPUTS["d14_frame_validity"].read_text(encoding="utf-8"))
    alias_map = {r["wtg"]: r.get("a_matched_alias") for r in d14["per_target"]}

    from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold
    splits = list(RepeatedStratifiedKFold(n_splits=3, n_repeats=10,
                                          random_state=SEED).split(np.zeros(n), y_str))
    splits3 = list(StratifiedKFold(n_splits=3, shuffle=True,
                                   random_state=SEED).split(np.zeros(n), y_str))
    diff = corpus_diff(dfs)
    print(f"[data] n={n} v2->v3 changed={diff['pairs']['v2->v3']['n_targets_changed']}", flush=True)

    cache = EncodeCache()
    e1 = exp1_embedding(dfs, cache, splits, y_idx, rng)
    e3 = exp3_field_ablation(dfs, cache, splits, y_idx)
    e4 = exp4_representation(dfs, cache, splits, y_idx, alias_map)
    e2 = exp2_tfidf(dfs, splits, y_str, splits3)

    gq = google_query_section(dfs, e1, e2, e3, e4, y_idx, google_i)
    noise = noise_analysis(e1, e2, e3, e4, y_idx, diff)

    # ---------------------------------------------------------- verdict grid
    rows = []

    def add(row, getter, note=""):
        d = {v: getter(v) for v in VERSIONS}
        rows.append({"row": row, **d, "changed_v1_to_v2": d["v1"] != d["v2"],
                     "changed_v2_to_v3": d["v2"] != d["v3"],
                     "changed_v1_to_v3": d["v1"] != d["v3"], "note": note})

    add("EXP1 RF001-C overall", lambda v: e1["per_version"][v]["verdict"])
    for hk in e1["per_version"]["v3"]["hypothesis_verdicts"]:
        add(f"EXP1 {hk}", lambda v, hk=hk: e1["per_version"][v]["hypothesis_verdicts"][hk])
    add("EXP2 RF001-B overall", lambda v: e2["per_version"][v]["verdict"])
    for hk in e2["per_version"]["v3"]["hypothesis_verdicts"]:
        add(f"EXP2 {hk}", lambda v, hk=hk: e2["per_version"][v]["hypothesis_verdicts"][hk])
    add("EXP3 RF2-C overall", lambda v: e3["per_version"][v]["verdict"])
    for hk in e3["per_version"]["v3"]["hypotheses"]:
        add(f"EXP3 {hk}", lambda v, hk=hk: e3["per_version"][v]["hypotheses"][hk])
    add("EXP4 D-SUP-01 overall", lambda v: e4["per_version"][v]["verdict"])
    add("EXP4 prior-based route", lambda v: e4["per_version"][v]["prior_based_route_verdict"])
    for hk in e4["per_version"]["v3"]["hypothesis_verdicts_priorfree"]:
        add(f"EXP4 {hk}", lambda v, hk=hk: e4["per_version"][v]["hypothesis_verdicts_priorfree"][hk])

    n_changed_23 = sum(r["changed_v2_to_v3"] for r in rows)
    n_changed_13 = sum(r["changed_v1_to_v3"] for r in rows)
    n_changed_12 = sum(r["changed_v1_to_v2"] for r in rows)

    if n_changed_13 == 0:
        h_robust, h_fragile = "SUPPORTED", "REFUTED"
    elif n_changed_13 > 0:
        h_robust, h_fragile = "PARTIALLY_SUPPORTED" if n_changed_23 == 0 else "REFUTED", "SUPPORTED"
    numeric_moved = any(
        abs(d.get("delta_v1_v3", 0.0) or 0.0) > 0.01
        for d in noise["per_experiment"].values() if isinstance(d.get("delta_v1_v3"), float))
    h_numeric = ("SUPPORTED" if (n_changed_13 == 0 and numeric_moved)
                 else ("NOT_SUPPORTED" if n_changed_13 > 0 else "PARTIALLY_SUPPORTED"))
    verdict = ("SUPPORTED" if n_changed_13 == 0
               else ("PARTIALLY_SUPPORTED" if n_changed_23 == 0 else "REFUTED"))

    superseding = []
    for r in rows:
        if r["changed_v2_to_v3"] or r["changed_v1_to_v3"]:
            superseding.append({
                "affected_row": r["row"], "v1": r["v1"], "v2": r["v2"], "v3": r["v3"],
                "supersedes": ("기존 D 산출물의 해당 판정은 오염 코퍼스 기준이다. 기존 파일은 고치지 않았고 "
                               "여기에 superseding finding 으로만 기록한다."),
                "authoritative_version": "v3"})

    doc = {
        "verdict": verdict,
        "rq_id": "RQ-D15",
        "hypothesis_id": "H-D15-CORPUS-ROBUSTNESS",
        "title": "코퍼스 결함 2건(인코딩·CSS)을 고친 v3 에서 NLP 계열 결론이 살아남는가",
        "hypothesis_verdicts": {
            "H-D15-ROBUST (결론 전부 유지)": h_robust,
            "H-D15-FRAGILE (최소 하나 역전)": h_fragile,
            "H-D15-NUMERIC_ONLY (수치만 이동, 판정 유지)": h_numeric},
        "generated_at_kst": datetime.now(KST).isoformat(),
        "seed": SEED, "n_expected": 56, "n_observed": n,
        "analysis_unit": "target state (in_mart==1), 1 row = 1 web target",
        "framing_D_FACT_01": {
            "statement": ("prior_archetype 과 prior_business_domain 은 이 56 target 표본에서 완전 "
                          "전단사다 (7↔7, MI = H = 2.311 bits, nMI 1.000, 56/56)."),
            "consequence": ("따라서 이 문서의 모든 prior_agreement 는 '업종 배정 재현율'이지 "
                            "대표기능 정확도가 아니다. accuracy 라고 부르지 않는다."),
            "source": "D_FACT_01_prior_domain_bijection.md / DSUP01 label_identifiability (재확인만, 재계산 아님)"},
        "corpus_defects_under_test": {
            "D-DEF-01": "lxml.html.fromstring(read_bytes()) 가 선언 charset 무시 → 한글 mojibake (v2 시정)",
            "D-DEF-04": "text_content() 가 <style>/<script>/<noscript>/<template> 텍스트 포함 (v3 시정)"},
        "inputs": {k: {"path": str(p), "sha256": sha256_file(p),
                       "bytes": p.stat().st_size} for k, p in INPUTS.items()},
        "firewall": {
            "not_opened": ["holdout label snapshot", "LABEL_SPLIT_FROZEN*", "HOLDOUT_FOR_C*",
                           "RAW_L1~L4*", "PACKET_L*", "*_OVERLAP*", "PRECEDENCE_CONTESTED*",
                           "CALIBRATION_FOR_B*", "**/control/**"],
            "statement": "위 경로군은 하나도 열지 않았다 (not_opened). 입력은 inputs 에 열거된 D 자체 산출물뿐이다.",
            "no_gold_labels_produced": True, "no_real_target_access": True,
            "no_network_download": True, "no_threshold_declared": True},
        "corpus_diff": diff,
        "verdict_grid": {
            "n_rows": len(rows), "n_changed_v1_to_v2": n_changed_12,
            "n_changed_v2_to_v3": n_changed_23, "n_changed_v1_to_v3": n_changed_13,
            "rows": rows},
        "exp1_embedding": e1,
        "exp2_tfidf": e2,
        "exp3_field_ablation": e3,
        "exp4_representation_ablation": e4,
        "google_and_query": gq,
        "version_delta_vs_noise": noise,
        "superseding_findings": superseding,
        "counterexamples": [],
        "limitation": "",
        "further_questions": [],
        "runtime_seconds": None,
    }

    # 반례 수집
    ce = []
    for r in rows:
        if r["changed_v1_to_v2"] or r["changed_v2_to_v3"]:
            ce.append(f"{r['row']}: v1={r['v1']} v2={r['v2']} v3={r['v3']} — 코퍼스 버전이 판정을 움직인 사례")
    gchanged = [k for k, vv in gq["google_prediction_changed_v2_to_v3"].items() if vv]
    if gchanged:
        ce.append("Google 예측이 v2→v3 에서 바뀐 경로: " + ", ".join(gchanged))
    for name, d in noise["per_experiment"].items():
        if isinstance(d.get("delta_v2_v3"), float) and d.get("delta_v2_v3_exceeds_fold_sd"):
            ce.append(f"{name}: v2→v3 delta {d['delta_v2_v3']:+.4f} 가 fold sd 보다 크다 — "
                      f"4/56 변경만으로 노이즈를 넘는 이동")
    doc["counterexamples"] = ce

    doc["limitation"] = (
        "n=56, 7 archetype 중 5개가 n<=5 (UTILITY 5 / COMMUNICATION 4 / PLACE 4 / QUERY 4 / "
        "CONTENT 3). per-class 수치는 Wilson CI 없이 읽으면 안 되고, QUERY 는 target 하나가 "
        "recall 을 0.25 씩 움직인다. v2→v3 에서 실제로 바뀐 target 이 4/56 뿐이라 이 replication 은 "
        "'CSS 오염 시정이 결론을 뒤집지 않는다'를 이 표본에서만 보인 것이며, CSS 오염이 더 넓게 "
        "퍼진 코퍼스에서도 같다고 말하지 않는다. 판정 규칙은 원 실험의 사전등록 규칙을 그대로 "
        "재사용했으므로 그 규칙 자체의 임의성(p2_5 > stratified mean 등)은 상속된다. "
        "모든 지표는 prior 재현율이지 대표기능 정확도가 아니다(D-FACT-01). causal claim 없음, "
        "best model 선정 없음, threshold/GO-NO-GO 없음.")
    doc["further_questions"] = [
        "v3 에서도 남아 있는 파싱 결함이 있는가 — hidden/aria-hidden 노드, SVG <title>, "
        "JSON-LD <script type=application/ld+json> 의 텍스트는 지금 어떻게 처리되고 있는가.",
        "landmarks/buttons 의 200자·80자 절단 규칙이 CSS 제거 후 어떤 target 에서 실질 내용을 "
        "여전히 자르는가 (Google 은 절단 경계가 바뀌면서 토큰이 52% 줄었다).",
        "QUERY n=4 를 늘리지 않고 QUERY 판정을 신뢰할 방법이 있는가 — 아니면 QUERY 는 "
        "구조적으로 판정 불가라고 선언해야 하는가.",
        "브랜드-only 대조군이 정당한 text featureset 을 계속 이긴다면, RF NLP fallback 은 "
        "무엇을 학습하고 있다고 봐야 하는가.",
    ]
    doc["runtime_seconds"] = round(time.time() - t_start, 1)

    figs = make_figures(doc)
    doc["figures"] = figs

    # 내부 키(_prefix) 는 남겨둔다: 재현·감사에 필요하고 크지 않다.
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str),
                        encoding="utf-8")
    print(f"[write] {OUT_JSON}  ({OUT_JSON.stat().st_size} bytes)", flush=True)
    print(f"[VERDICT] {verdict}  grid rows={len(rows)} changed v1->v2={n_changed_12} "
          f"v2->v3={n_changed_23} v1->v3={n_changed_13}", flush=True)

    # ---------------------------------------------------------------- MLflow
    sys.path.insert(0, str(RD / "tools"))
    import mlflow
    import mlflow_contract as C
    with C.research_run(
            experiment="LA_03_RF_MAPPING", run_name="RQ-D15 v3 corpus replication",
            plane="D", agent_id="D", subagent_id="worker/RQ-D15",
            objective="코퍼스 결함 2건(인코딩·CSS)을 고친 v3 에서 NLP 계열 결론이 살아남는가",
            method="v1/v2/v3 격자 재현 — 임베딩 prototype · TF-IDF(브랜드 대조군 포함) · field ablation · representation ablation",
            dataset_grain="target (in_mart==1), n=56",
            n_expected=56, n_observed=56,
            hypothesis_id="H-D15-CORPUS-ROBUSTNESS",
            competing_hypothesis="ROBUST 전부 유지 / FRAGILE 최소 하나 역전 / NUMERIC_ONLY 수치만 변동",
            claim_kind="ANALYSIS", ticket_id="NONE", phase="I1", split="none", parent_run_id="NONE",
            result_path=OUT_JSON,
            model_or_rule_version="D15_V3_REPLICATION_v1", seed=SEED,
            code_path=Path(__file__),
            notebook="RQ_D15_v3_replication.ipynb",
            extra_tags={"rq_id": "RQ-D15", "corpus_version": "v3",
                        "replicates": "RF001-B, RF001-C, RF2-C, D-SUP-01",
                        "supersedes_nothing": "true",
                        "corpus_sha_v1": diff["sha256"]["v1"],
                        "corpus_sha_v2": diff["sha256"]["v2"],
                        "corpus_sha_v3": diff["sha256"]["v3"],
                        "verdict_grid_changed_v2_v3": str(n_changed_23),
                        "verdict_grid_changed_v1_v3": str(n_changed_13)}) as run:
        m = {}
        for v in VERSIONS:
            m[f"exp1.{v}.primary_macro_f1"] = e1["per_version"][v]["primary"]["macro_f1"]
            m[f"exp1.{v}.primary_prior_agreement"] = e1["per_version"][v]["primary"]["prior_agreement"]
            m[f"exp1.{v}.n_configs_beating_stratified_p95"] = float(
                e1["per_version"][v]["prototype_sensitivity"]["global"]["n_configs_beating_stratified_p95"])
            m[f"exp2.{v}.primary_macro_f1_mean"] = e2["per_version"][v]["primary_result"]["summary"]["mean"]
            m[f"exp2.{v}.brand_only_best_macro_f1"] = e2["per_version"][v]["brand_leak_test"]["brand_only_best_macro_f1"]
            m[f"exp3.{v}.rank1_macro_f1"] = e3["per_version"][v]["headline"]["best_macro_f1"]
            m[f"exp3.{v}.text_blob_macro_f1"] = e3["per_version"][v]["headline"]["text_blob_macro_f1"]
            m[f"exp3.{v}.best_control_macro_f1"] = e3["per_version"][v]["headline"]["best_control_macro_f1"]
            E1p = e4["per_version"][v]["E1_which_surface_drives_FULL"][PRIMARY_PROTO]
            m[f"exp4.{v}.topic_reproduces_full"] = E1p["topic_reproduces_full"]
            m[f"exp4.{v}.control_reproduces_full"] = E1p["control_reproduces_full"]
            m[f"exp4.{v}.mcnemar_p"] = E1p["mcnemar_exact"]["p_two_sided"]
        m["grid.n_rows"] = float(len(rows))
        m["grid.n_changed_v1_to_v2"] = float(n_changed_12)
        m["grid.n_changed_v2_to_v3"] = float(n_changed_23)
        m["grid.n_changed_v1_to_v3"] = float(n_changed_13)
        m["corpus.n_targets_changed_v2_to_v3"] = float(diff["pairs"]["v2->v3"]["n_targets_changed"])
        m["corpus.n_targets_changed_v1_to_v3"] = float(diff["pairs"]["v1->v3"]["n_targets_changed"])
        mlflow.log_metrics({k: float(val) for k, val in m.items()})
        mlflow.log_params({"corpus_v1_sha": diff["sha256"]["v1"][:16],
                           "corpus_v2_sha": diff["sha256"]["v2"][:16],
                           "corpus_v3_sha": diff["sha256"]["v3"][:16],
                           "models": ",".join(MODELS),
                           "prototype_sets": ",".join(PROTO_SETS),
                           "cv": "RepeatedStratifiedKFold(3,10,seed=20260827)",
                           "n_mc_permutations": N_MC,
                           "n_tfidf_permutations": N_PERM_TFIDF})
        mlflow.log_text(json.dumps(doc["verdict_grid"], ensure_ascii=False, indent=1),
                        "verdict_grid.json")
        mlflow.log_text(json.dumps(doc["google_and_query"], ensure_ascii=False, indent=1,
                                   default=str), "google_and_query.json")
        mlflow.log_text(json.dumps(doc["version_delta_vs_noise"], ensure_ascii=False, indent=1,
                                   default=str), "version_delta_vs_noise.json")
        mlflow.log_text(json.dumps(doc["corpus_diff"], ensure_ascii=False, indent=1),
                        "corpus_diff.json")
        for name, path in figs.items():
            mlflow.log_artifact(path, artifact_path="figures")
        C.log_pointer("RQ_D15_v3_replication.json", str(OUT_JSON), sha256_file(OUT_JSON),
                      OUT_JSON.stat().st_size)
        C.finish(verdict=verdict, limitation=doc["limitation"])
        run_id = run.info.run_id

    doc["mlflow_run_id"] = run_id
    doc["mlflow_experiment"] = "LA_03_RF_MAPPING"
    doc["result_sha_note"] = ("MLflow tag result_sha 는 mlflow_run_id 를 적기 전 버전의 sha256 이다 "
                              "(D-SUP-01 과 동일한 관례).")
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str),
                        encoding="utf-8")
    print(f"[mlflow] run_id={run_id}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
