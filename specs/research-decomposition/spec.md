# research-decomposition Specification

## Purpose
定义基于多视角枚举的课题拆分与调研规划规范。系统将总体研究目标分解为带 DAG 依赖的有向无环任务清单，为每个任务注入可校验的 guidelines 约束，并确保完全覆盖简报中的全部需求索引。

## Requirements

### Requirement: Perspective-Driven Task Decomposition
The system SHALL decompose the research topic into task.json containing structured fields and a strictly acyclic dependency graph.

#### Scenario: Valid task schema and acyclic DAG validation
- **WHEN** python3 scripts/task_schema_check.py task.json --schema schemas/task.schema.json is executed
- **THEN** the process exit code is 0
- **AND** stdout JSON contains {"errors":[]}
- **AND** the task graph contains 0 circular dependencies

### Requirement: Task Guidelines and Three Data Essentials
The system SHALL enforce non-empty guidelines for every task entry asserting source provenance, reference date, and metric standard.

#### Scenario: Missing guidelines in task entry triggers validation failure
- **WHEN** a task entry in task.json lacks assertions for source URL, pricing date, or metric unit
- **THEN** python3 scripts/task_schema_check.py returns exit code 1
- **AND** stdout JSON lists the offending task_id and missing essential fields

### Requirement: Complete REQ-ID Index Coverage
The system MUST verify that all REQ-ID entries declared in brief.md are covered by target_req_ids in task.json.

#### Scenario: Set containment verification of requirement IDs
- **WHEN** python3 scripts/task_schema_check.py task.json --req-index brief.md --coverage is executed
- **THEN** the difference set of brief REQ-IDs minus task.json target_req_ids is empty
- **AND** stdout JSON contains {"uncovered_req_ids":[],"coverage_ratio":1.0}
- **AND** the process exit code is 0
