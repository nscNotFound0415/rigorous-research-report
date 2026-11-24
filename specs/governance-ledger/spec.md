# governance-ledger Specification

## Purpose
定义项目进度、授权与决策合一的治理台账与存储载体适配契约。系统通过四分状态公理消除隐式进展假象，确保台账复选框勾选权归人类排他所有，并拦截未登记的文件写操作。

## Requirements

### Requirement: Four-Fold State Axiom Ledger Tracking
The system SHALL maintain all 15 pipeline tasks in progress-log.md with explicit four-fold state enumeration and separate checkbox completion.

#### Scenario: Ledger records four-fold state column
- **WHEN** progress-log.md is inspected after phase initialization
- **THEN** each task row contains a "四分状态" column with values strictly restricted to "存在", "已复核", "已同步", or "已审定"
- **AND** the task list contains exactly 15 defined task rows with standardized IDs from T-P1-01 to T-M8-01

#### Scenario: Invalidation marks affected rows as STALE without altering checkboxes
- **WHEN** change propagation marks affected tasks as STALE
- **THEN** affected task rows in progress-log.md display STALE in the four-fold state column
- **AND** the completion checkboxes remain unmodified

### Requirement: Checkbox Ownership and Anti-Forgery Protection
The system SHALL prohibit agent sessions from writing [x] into the task completion column and MUST roll back unauthorized modifications.

#### Scenario: Agent attempts unauthorized self-approval checkbox write
- **WHEN** an agent writes "[x]" into the completion column without a valid gates/*.md approval record
- **THEN** python3 scripts/storage_guard.py --check-ledger reverts the unauthorized checkbox to "[ ]"
- **AND** the unauthorized attempt is recorded in violations.log
- **AND** the process exit code is 1

#### Scenario: Human signoff authorizes checkbox update
- **WHEN** an approval file gates/G1-approval.md exists with decision APPROVED and valid human signature
- **THEN** task T-G1-01 is marked with "[x]" and references the approval file name and SHA-256 hash
- **AND** python3 scripts/gate_guard.py returns exit code 0

### Requirement: Decision Record Binding for Checked Task Rows
The system SHALL bind every checked task row to an approved_by: human decision record whose artifact_sha256 equals the recorded artifact hash.

#### Scenario: Checked row without human decision record or with mismatched hash is rejected
- **WHEN** python3 scripts/storage_guard.py --root <dir> --check-decision-log is executed on progress-log.md whose "[x]" row lacks an approved_by: human decision record or whose artifact_sha256 differs from the recorded artifact
- **THEN** the process exit code is 1
- **AND** stdout JSON contains {"decision_log_valid":false,"violations":[...]} with the offending ledger line number

#### Scenario: Checked row bound to a matching human decision record passes
- **WHEN** python3 scripts/storage_guard.py --root <dir> --check-decision-log is executed on progress-log.md whose "[x]" row carries approved_by: human and an artifact_sha256 equal to the recorded artifact hash
- **THEN** the process exit code is 0
- **AND** stdout JSON contains {"decision_log_valid":true,"violations":[]}

### Requirement: Brief Source-of-Truth Enum Validation
The system MUST reject any brief.md whose source_of_truth value is absent, pending, or outside the two permitted enumerations ONLINE_AUTHORITATIVE and LOCAL_AUTHORITATIVE.

#### Scenario: Out-of-enum source_of_truth value is rejected
- **WHEN** python3 scripts/gate_guard.py --verify-brief brief.md is executed on a brief.md whose source_of_truth is LOCAL_GIT_FIRST, empty, or any non-enumerated value
- **THEN** the process exit code is 1
- **AND** stdout JSON contains {"valid":false} with an errors entry naming the invalid source_of_truth value

#### Scenario: Either permitted source_of_truth value passes
- **WHEN** python3 scripts/gate_guard.py --verify-brief brief.md is executed on a brief.md whose source_of_truth is ONLINE_AUTHORITATIVE or LOCAL_AUTHORITATIVE
- **THEN** the process exit code is 0
- **AND** stdout JSON contains {"valid":true,"errors":[]}

### Requirement: Controlled Storage and Manifest Registration
The system MUST intercept and reject any file creation or modification not declared in manifest.json.

#### Scenario: Unregistered file write attempt is rejected
- **WHEN** python3 scripts/storage_guard.py --root . --manifest manifest.json --probe-unregistered-write detects an unmanaged file path
- **THEN** the process returns exit code 0 indicating successful rejection
- **AND** stdout JSON contains {"rejected":true} with the offending file path
