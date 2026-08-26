"""P-C FIXTURE ENGINEERING — L0/L1 측정엔진의 구조·로직을 로컬/합성 픽스처로 검증한다.

레인 성격 (research/landing_accessibility CLAUDE.md 상속 + 오케스트레이터 프롬프트):
    - SHADOW / PREPARATORY. Gate 를 스스로 닫지 않는다.
    - 실제 서비스 URL 을 열지 않는다 — Playwright 는 쓰지만 목적지는 항상 로컬
      ``file://`` 픽스처다.
    - 여기서 나오는 어떤 값도 실제 KWCAG verdict·MPFED·NED/IED 로 인용하지 않는다.
      전부 "메커니즘이 동작하는가"를 검증하기 위한 합성 데이터다.

이 패키지는 ``research/refcohort`` (Pilot, READ_ONLY) 의 4종 증거 수집·판정
설계를 참고하되, Pilot 자체 감사(``research/refcohort/audit/findings_registry.jsonl``)가
확인한 다음 결함을 반복하지 않도록 설계를 바꿨다.

    evidence-filename-collision-overwrite (CRITICAL) -> identity.observation_id (hash 기반)
    append-only-not-enforced (MEDIUM)                -> guarded_writer.GuardedEvidenceWriter
    scope-relation-suffix-truncation (HIGH)           -> domain_scope.registrable_domain
    gate-detection-false-negative (MEDIUM)            -> gate.detect_gate (다중 신호 + 근거 기록)
    no-interaction-evidence-but-called-complete (MED) -> static_evidence_complete / interaction_evidence_present 분리
    duplicate-endpoints-double-counted (HIGH)         -> dedup.assert_measured_records_unique
    guard-blind-to-na-undetermined-laundering (CRIT)  -> verdict.CriterionObservation (구성 시점 강제)
    undetermined-absorbed-into-pass (HIGH)            -> verdict.derive_verdict_state

evidence 파일 인벤토리(``manifest.jsonl``)는 이 패키지가 새로 발명하지 않는다.
기존 ``landing_accessibility.evidence_manifest`` (``docs/07_EVIDENCE_MANIFEST_CONTRACT.md``)
의 스키마(``observation_id``/``relpath``/``sha256``/``bytes``)를 그대로 쓰고,
이 패키지는 그 위에 "수집 시점에 append-only 를 실제로 강제하는 계층"만 얹는다.

## A0 SHADOW/PREPARATORY 정책 (``docs/v2/PHASE_GATES.md`` §4, 2026-08-27)

이 패키지의 모든 진입점은 ``execution_mode`` 를 필수 키워드 인자로 받는다
(``execution_mode.py``). P0 종료 전에는 ``FIXTURE`` 또는 ``SHADOW_DRY_RUN`` 만
허용되고, ``REAL_TARGET`` 은 hard FAIL 이다 — REAL-TARGET FIREWALL, §4.5.

이 패키지가 쓰는 모든 observation/run 산출물은 ``provenance.py`` 가 만드는
동일한 provenance 블록(``created_before_p0_close`` / ``authoritative=false`` /
``requires_post_p0_reconciliation`` 등, §4.3)을 갖는다.
"""

from __future__ import annotations
