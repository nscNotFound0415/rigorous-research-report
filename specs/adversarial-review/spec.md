# adversarial-review Specification

## Purpose
定义三产物边界的通用对抗复核循环、四档缺陷分流与机器可读调用证明规范。系统在只读沙箱中调度隔离模型，产出结构化缺陷对照稿，并执行四层回读复验。

## Requirements

### Requirement: Reviewer Isolation and Machine-Readable Provenance
The system SHALL execute review in a read-only sandbox and generate review-reports/<boundary>_provenance.json recording writer and reviewer identities.

#### Scenario: Non-homologous model review passes isolation check
- **WHEN** python3 scripts/gate_guard.py --check-provenance review-reports/<boundary>_provenance.json is executed with channel "异族" and differing model vendor prefixes
- **THEN** the isolation check passes with exit code 0
- **AND** stdout JSON contains {"provenance_valid":true,"isolated":true}
- **AND** writer.session is distinct from reviewer.session

#### Scenario: Unverified isolation or missing provenance fails gate
- **WHEN** python3 scripts/gate_guard.py --check-provenance review-reports/<boundary>_provenance.json is executed on provenance with matching session IDs or claiming isolation without context_reset true
- **THEN** the process exit code is 1
- **AND** stdout JSON contains {"provenance_valid":false,"isolated":false}
- **AND** the boundary is marked BLOCKED_NO_REVIEWER

### Requirement: Four-Tier Defect Triage (D0-D3)
The system SHALL classify findings into D0 confirmed errors, D1 insufficient evidence, D2 source conflicts, or D3 pending T-items. Every D0 defect MUST carry a route field strictly set to ARITH, QUOTE_MISMATCH, or LEXICAL_RULE; all three routes are machine-decidable with no subjective judgement. Directional logic contradictions and unstated conjectures SHALL NOT be D0 and MUST be triaged into D1 or D3. D1 defects SHALL present exactly two options at Gate G2 without automatic machine rewrite.

#### Scenario: Mandatory zero D0 defects for boundary exit
- **WHEN** review-reports/<boundary>_review.md contains 1 or more D0 defects
- **THEN** the boundary exit check returns exit code 1
- **AND** progression to downstream stages is blocked until all D0 defects are corrected

#### Scenario: D0 classification strictly restricted to ARITH, QUOTE_MISMATCH, and LEXICAL_RULE routes
- **WHEN** review-reports/<boundary>_review.md is generated
- **THEN** every D0 defect item contains a route field strictly set to ARITH, QUOTE_MISMATCH, or LEXICAL_RULE
- **AND** ARITH items carry a recomputation command and its output line, QUOTE_MISMATCH items carry the source chunk ID and the inconsistent excerpt (NOT_FOUND when absent), and LEXICAL_RULE items carry a machine scanner command and its output line
- **AND** LEXICAL_RULE covers meta-narration, dangling references, and figure/table numbering gaps judged by deterministic scanners
- **AND** unprovable directional logic and subjective conjectures are triaged into D1 or D3
- **AND** D1 items present exactly two options ("补证" | "降级为推测/待证实") for human adjudication at Gate G2 without automatic machine rewrite

### Requirement: Four-Layer Readback Verification
The system MUST verify partial text replacements via python3 scripts/verify_readback.py satisfying all four verification layers.

#### Scenario: Clean patch replacement satisfies all four layers
- **WHEN** python3 scripts/verify_readback.py --plan correction-diff.md --target draft_full.md is executed after applying approved corrections
- **THEN** layer1 new sentences are 100% present in the target
- **AND** layer2 D0 old sentence residual count is 0
- **AND** layer3 structural block counts match expected values
- **AND** layer4 content_sha256 and nettext_sha256 match declared values
- **AND** the process exit code is 0
