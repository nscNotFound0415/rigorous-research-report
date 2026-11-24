# outline-approval Specification

## Purpose
定义章节论证拓扑规划、前置证据引用回指与 G1 人审审批门禁规范。系统在并行期消费调研索引快照，在 Join 2 汇合前强制清零待补数据，并通过 G1 签署锁定结构性反馈。

## Requirements

### Requirement: Outline Structuring and Evidence Backlink
The system SHALL structure outline.md with section contracts and verify that all data citations link to valid evidence-index.md entries or explicit PENDING items.

#### Scenario: Parallel phase permits explicit PENDING citations
- **WHEN** outline.md is drafted during parallel execution with M4
- **THEN** every citation contains an evidence_ref linking to an existing evidence index entry or is marked PENDING
- **AND** all PENDING citations are listed in the explicit "待补数据" section of outline.md

#### Scenario: Join 2 barrier mandates zero PENDING citations
- **WHEN** the Join 2 barrier check is executed prior to G1 approval
- **THEN** the count of PENDING evidence citations in outline.md is 0
- **AND** all cited evidence IDs exist in evidence-index.md

### Requirement: Gate G1 Human Approval and Workflow Interception
The system MUST require a valid gates/G1-approval.md before allowing drafting module M7 to initiate.

#### Scenario: Missing or rejected G1 approval blocks drafting
- **WHEN** python3 scripts/gate_guard.py --gate G1 --check-only is executed while G1-approval.md is missing or has decision REJECTED
- **THEN** the process exit code is 1
- **AND** drafting execution request is blocked with 0 bytes written to draft_full.md

#### Scenario: Approved G1 permits synthesis progression
- **WHEN** gates/G1-approval.md contains valid human signature and decision APPROVED with matching artifact_sha256
- **THEN** python3 scripts/gate_guard.py --gate G1 --verify --artifact outline.md --approval gates/G1-approval.md returns exit code 0
- **AND** the state in stdout JSON is APPROVED
