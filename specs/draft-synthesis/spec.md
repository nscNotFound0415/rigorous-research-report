# draft-synthesis Specification

## Purpose
定义单次全文合稿、白名单文本卫生扫描、直写 OOXML 与交付双向回读校验规范。系统杜绝分节拼接，保护 9 类必要严谨性声明，并通过两遍法确保 Word 与 PDF 交付物目录零误差。

## Requirements

### Requirement: Monolithic Drafting and Synthesis Consistency Pass
The system SHALL synthesize draft_full.md in a single monolithic pass and execute polish checks to ensure terminology uniformity and deduplication.

#### Scenario: Section deduplication verification passes
- **WHEN** draft_full.md is inspected for inter-section redundancy
- **THEN** the count of shared continuous substrings with length >= 30 characters between any two distinct sections is 0

### Requirement: Text Hygiene Audit with Allowlist Protection
The system SHALL scan draft_full.md using templates/forbidden_terms.json and verify 0 unallowlisted meta-narrative violations while preserving all 9 rigor declaration types.

#### Scenario: Prohibited meta-narrative outside allowlist triggers rejection
- **WHEN** draft_full.md contains unallowlisted phrases matching forbidden patterns
- **THEN** python3 scripts/audit_text_hygiene.py draft_full.md --rules templates/forbidden_terms.json returns exit code 1
- **AND** stdout JSON contains non-empty violations list

#### Scenario: Allowlisted rigor declarations pass without false positives
- **WHEN** draft_full.md contains permitted rigor declarations listed in allowlist
- **THEN** python3 scripts/audit_text_hygiene.py returns exit code 0
- **AND** stdout JSON contains {"violations":[]}

### Requirement: Dual Document Build and Delivery Readback Verification
The system MUST generate docx via direct OOXML writing, pdf via headless soffice, execute two-pass TOC backfill, and verify zero difference sets.

#### Scenario: Delivery readback confirms zero heading and page mismatches
- **WHEN** python3 scripts/delivery_readback.py --docx delivery/output.docx --pdf delivery/output.pdf --source draft_full.md is executed
- **THEN** toc_minus_headings is an empty array
- **AND** headings_minus_toc is an empty array
- **AND** page_mismatch is an empty array
- **AND** the process exit code is 0

#### Scenario: Idempotent build produces identical component hashes
- **WHEN** draft_full.md is built twice consecutively into docx
- **THEN** all component part hashes in build_manifest.json are identical between both runs

### Requirement: Figure Table Numbering and Citation Anchoring
The system SHALL verify continuous figure and table numbering in draft_full.md and MUST confirm every in-text citation resolves to an entry in evidence-index.md.

#### Scenario: All citations anchored and figure numbering continuous
- **WHEN** python3 scripts/citation_check.py draft_full.md --evidence-index evidence-index.md is executed on a fully anchored draft
- **THEN** the process exit code is 0
- **AND** stdout JSON contains {"dangling_refs":[],"unnumbered_figs":[],"dangling_tables":[]}

#### Scenario: Dangling citation or broken figure numbering is rejected
- **WHEN** python3 scripts/citation_check.py draft_full.md --evidence-index evidence-index.md is executed on a draft containing an unresolved evidence reference or a skipped figure number
- **THEN** the process exit code is 1
- **AND** stdout JSON lists the offending reference id or figure number in dangling_refs or unnumbered_figs

### Requirement: Final Delivery Gate G3 Human Sign-Off
The system MUST block external delivery until gates/G3-approval.md carries decision APPROVED, a human signature, and an artifact_sha256 matching the delivered artifact.

#### Scenario: Missing G3 sign-off blocks delivery
- **WHEN** python3 scripts/gate_guard.py --gate G3 --check-only is executed while gates/G3-approval.md is missing
- **THEN** the process exit code is 1
- **AND** stdout JSON contains {"gate":"G3","state":"PENDING","blocked":true}

#### Scenario: Valid human G3 sign-off with matching hash permits delivery
- **WHEN** gates/G3-approval.md contains a human signature, decision APPROVED, and artifact_sha256 matching delivery/output.docx
- **THEN** python3 scripts/gate_guard.py --gate G3 --verify --artifact delivery/output.docx --approval gates/G3-approval.md returns exit code 0
- **AND** stdout JSON contains {"gate":"G3","state":"APPROVED","blocked":false}

#### Scenario: Machine or stub G3 sign-off is rejected with correct hash
- **WHEN** gates/G3-approval.md declares a machine signer or stub: true while its artifact_sha256 matches delivery/output.docx
- **THEN** the process exit code is 1
- **AND** stdout JSON contains blocked true with state AGENT_SIGNATURE_PROHIBITED or STUB_REJECTED
