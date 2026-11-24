# fact-verification Specification

## Purpose
定义数据底表构建、双通道事实核验与口径分栏隔离规范。系统将一手证据归档至事实库，对数值计算执行纯代码算术复算，对引用执行一手快照比对，并强制阻断跨口径加减运算。

## Requirements

### Requirement: Code-Based Arithmetic Audit with Tolerance
The system SHALL audit all formula cells in datatable.csv against expected expressions within declared tolerance values.

#### Scenario: Formula calculation within declared tolerance passes
- **WHEN** python3 scripts/audit_calc.py datatable.csv is executed on verified formula cells
- **THEN** the process exit code is 0
- **AND** stdout JSON contains {"checked_cells":N,"mismatches":[]} where mismatches count is 0

#### Scenario: Calculation mismatch triggers failure and coordinate output
- **WHEN** a calculated value differs from the expected expression by more than the declared tolerance
- **THEN** python3 scripts/audit_calc.py returns exit code 1
- **AND** stdout JSON reports the row and column coordinates of the mismatch

### Requirement: Data Source Classification and Assumption Tagging
The system SHALL require every datatable cell to have an explicit source_type and MUST mandate non-empty assumption_tag when source_type is estimated.

#### Scenario: Estimated cell without assumption tag is rejected
- **WHEN** datatable.csv contains a cell with source_type estimated but empty assumption_tag
- **THEN** python3 scripts/audit_calc.py returns exit code 1
- **AND** stdout JSON reports the invalid cell coordinate

### Requirement: Scope Isolation and Cross-Scope Arithmetic Ban
The system MUST enforce explicit separator columns between different metric scopes and prohibit cross-scope addition or subtraction.

#### Scenario: Direct arithmetic across incompatible scopes is blocked
- **WHEN** a formula references cells across distinct scope columns without normalization
- **THEN** python3 scripts/audit_calc.py returns exit code 1
- **AND** stdout JSON flags a scope isolation violation error
