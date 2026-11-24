# change-circuit Specification

## Purpose
定义外部指示响应、变更对照表处置、母本冻结与零漂移回读核验规范。系统以对照表与签署件为基线通路，在修改前锁定母本哈希并在修改后验证非声明区域零漂移。

## Requirements

### Requirement: Change Matrix Dispatch and Ceremony Triage
The system SHALL record all external change requests into change-table.md and assign ceremony levels before touching baseline files.

#### Scenario: Change table records directive and target sections
- **WHEN** an external change directive is received
- **THEN** change-table.md records change_id, parent_baseline_sha256, target section, old text, and proposed new text
- **AND** ceremony_level is set to LIGHTWEIGHT by default

#### Scenario: Change propagation identifies stale targets without baseline rewrite
- **WHEN** python3 scripts/change_dispatch.py --propagate --instruction-file <file> is executed
- **THEN** the process returns exit code 0
- **AND** stdout JSON contains {"propagated":true,"rewritten":false}
- **AND** affected ledger tasks are marked STALE while baseline documents remain unmodified

### Requirement: Baseline Freeze and Signoff Gate
The system MUST freeze the parent baseline artifact and require gates/change-<id>-approval.md before any write operation is permitted.

#### Scenario: Modification without change signoff is blocked
- **WHEN** python3 scripts/gate_guard.py --gate change-01 --check-only is executed without approval
- **THEN** the process exit code is 1
- **AND** stdout JSON contains {"gate":"change-01","state":"PENDING","blocked":true}
- **AND** the parent baseline file content_sha256 remains unmodified

### Requirement: Zero-Drift Readback and Snapshot Archival
The system SHALL create a read-only backup snapshot and verify zero undeclared drift in non-targeted sections after change execution.

#### Scenario: Diff verification confirms zero undeclared drift
- **WHEN** python3 scripts/verify_readback.py --diff-mode --old backup/old_rev.md --new draft_full.md --declared C-01 is executed
- **THEN** the process exit code is 0
- **AND** stdout JSON contains {"undeclared_drift":0}
- **AND** backup/ contains the full pre-change baseline snapshot matching parent_baseline_sha256

#### Scenario: Pre-change backup snapshot archive is verified independently
- **WHEN** python3 scripts/verify_readback.py --verify-backup backup/ --change-table change-table.md is executed
- **THEN** the process exit code is 0
- **AND** stdout JSON contains {"backup_valid":true,"hash_matched":true,"snapshot_path":"..."} when backup/ exists with 1 or more files whose hash equals parent_baseline_sha256

#### Scenario: Missing or hash-mismatched backup snapshot is rejected
- **WHEN** python3 scripts/verify_readback.py --verify-backup backup/ --change-table change-table.md is executed while backup/ is empty, missing, or its file hash differs from parent_baseline_sha256
- **THEN** the process exit code is 1
- **AND** stdout JSON contains {"backup_valid":false,"hash_matched":false}
