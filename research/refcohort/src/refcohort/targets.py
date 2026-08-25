"""측정 대상 두 코호트를 만든다.

  REFERENCE  = 감사일 기준 유효한 공식 인증 endpoint (국가가 '지침을 지켰다'고 인정한 표본)
  COMPARISON = 50+ 실사용 상위 서비스 (엑셀 evidence row, 대부분 인증 없음)

엑셀 원칙: 행은 삭제하지 않는다. 같은 서비스가 여러 지표에 반복 등장하는 것은
실사용 근거의 중복이 아니라 근거의 누적이므로, canonical service 하나에 evidence row 여럿을 연결한다.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

# 엑셀 Primary 유형 → 프로토콜 v2 과업 코드
TYPE_MAP = {
    "BUY_RESERVE": "BUY",
    "MOBILITY_MAP": "MAP",
    "TRANSFER_ENTRY": "TRANSFER",
    "COMMUNITY_PARTICIPATION": "COM",
    "SEARCH_INFO": "SEARCH",
    "CULTURE_EDU": "CULTURE",
    "HEALTH_WELFARE": "HEALTH",
    "PUBLIC": "PUBLIC",
    "OTHER_UTILITY": "OTHER",
    "DELIVERY": "DELIVERY",
    "VOTE": "VOTE",
    "SHARE": "SHARE",
    "CALL": "CALL",
    "PARTNER": "PARTNER",
}

# 인증 서비스명·기관명 → 과업 코드 분류 규칙 (전수 크롤 후 적용, 키워드 검색 대체)
CLASSIFY_RULES: list[tuple[str, str]] = [
    (r"주차|교통|버스|지하철|철도|지도|길찾기|내비|위치|관광지도|도로", "MAP"),
    (r"은행|금융|뱅킹|카드|보험|증권|송금|이체|여신|저축|공제|캐피탈|페이|결제", "TRANSFER"),
    (r"쇼핑|몰\b|마트|백화점|스토어|구매|주문|장터|판매|상품|홈쇼핑", "BUY"),
    (r"배송|택배|우편|물류|배달", "DELIVERY"),
    (r"선거|투표|여론|설문|참여|청원|제안", "VOTE"),
    (r"상담|문의|고객센터|콜센터|메신저|채팅|민원상담", "COM"),
    (r"영상|사진|미디어|방송|아카이브|콘텐츠|갤러리|공유", "SHARE"),
    (r"통화|전화|보이는\s*ARS", "CALL"),
    (r"제휴|협력|연계|파트너", "PARTNER"),
    (
        r"민원|공공|정부|시청|구청|군청|도청|공단|공사|진흥원|연구원|위원회|재단|협회|센터|청\b|부\b|처\b|원\b|교육청|대학교|병원|도서관|박물관|미술관",
        "PUBLIC",
    ),
]


@dataclass
class Target:
    record_id: str
    cohort: str  # REFERENCE | COMPARISON
    service_name: str
    url: str
    primary_task_code: str
    organization_name: str | None = None
    certification_number: str | None = None
    cert_start_date: str | None = None
    cert_end_date: str | None = None
    certification_status_observed: str | None = None
    url_status: str | None = None
    evidence_rows: list[dict] = field(default_factory=list)
    source: str = ""

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        return d


def classify(service_name: str, org: str | None = None) -> str:
    """서비스명·기관명으로 과업 코드를 분류한다. 규칙 순서가 우선순위다."""
    hay = f"{service_name or ''} {org or ''}"
    for pattern, code in CLASSIFY_RULES:
        if re.search(pattern, hay):
            return code
    return "OTHER"


def normalize_url(u: str | None) -> str | None:
    if not u:
        return None
    u = u.strip()
    if not u:
        return None
    if not u.startswith(("http://", "https://")):
        u = "https://" + u.lstrip("/")
    p = urlparse(u)
    if not p.netloc:
        return None
    return u


def build_reference(registry_path: Path, audit: date, *, valid_only: bool = True) -> list[Target]:
    rows = [
        json.loads(x) for x in registry_path.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    out: list[Target] = []
    for r in rows:
        if valid_only and r.get("cert_valid_candidate_o") != "O":
            continue
        url = normalize_url(r.get("certified_target_url_listed"))
        if not url:
            continue
        seq = r.get("certification_number") or "unknown"
        out.append(
            Target(
                record_id=f"REF:{seq}",
                cohort="REFERENCE",
                service_name=r.get("service_name") or "",
                url=url,
                primary_task_code=classify(r.get("service_name"), r.get("organization_name")),
                organization_name=r.get("organization_name"),
                certification_number=seq,
                cert_start_date=r.get("cert_start_date_listed"),
                cert_end_date=r.get("cert_end_date_listed"),
                certification_status_observed=r.get("certification_status_listed"),
                url_status="CERTIFIED_TARGET_URL",
                source="kwacc_full_registry",
            )
        )
    return out


def build_comparison(xlsx_path: Path) -> list[Target]:
    """엑셀 06_전체원자료를 canonical service 단위로 묶되 evidence row를 모두 보존한다."""
    import pandas as pd

    df = pd.read_excel(xlsx_path, sheet_name="06_전체원자료")
    grouped: dict[str, Target] = {}
    for _, row in df.iterrows():
        name = str(row["앱/서비스"]).strip()
        raw_url = row.get("공식 URL 후보")
        url = normalize_url(None if (raw_url is None or str(raw_url) == "nan") else str(raw_url))
        ptype = TYPE_MAP.get(str(row.get("Primary 유형")).strip(), "OTHER")
        ev = {
            "패널": row.get("패널"),
            "순위": None if str(row.get("순위")) == "nan" else int(row.get("순위")),
            "값": None if str(row.get("값")) == "nan" else float(row.get("값")),
            "단위": row.get("단위"),
        }
        key = name
        if key in grouped:
            grouped[key].evidence_rows.append(ev)
            continue
        grouped[key] = Target(
            record_id=f"CMP:{re.sub(r'[^0-9A-Za-z가-힣]+', '_', name)[:40]}",
            cohort="COMPARISON",
            service_name=name,
            url=url or "",
            primary_task_code=ptype,
            url_status=str(row.get("URL 상태")),
            evidence_rows=[ev],
            source="50plus_all_rankings_real_url_mapping.xlsx#06_전체원자료",
        )
    return list(grouped.values())


def summarize(targets: list[Target]) -> dict:
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for t in targets:
        by_type[t.primary_task_code] = by_type.get(t.primary_task_code, 0) + 1
        by_status[t.url_status or "NONE"] = by_status.get(t.url_status or "NONE", 0) + 1
    return {
        "count": len(targets),
        "with_url": sum(1 for t in targets if t.url),
        "without_url": sum(1 for t in targets if not t.url),
        "by_primary_task_code": dict(sorted(by_type.items(), key=lambda x: -x[1])),
        "by_url_status": by_status,
    }
