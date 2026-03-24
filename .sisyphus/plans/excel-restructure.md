# Excel Output Restructure

## TL;DR

> **Quick Summary**: Restructure Excel output to replace multiple "By X" summary sheets with per-resource-type sheets (ECS, Database, OSS) that combine filtered results with relevant summaries, and convert Summary sheet to clean table format.
> 
> **Deliverables**:
> - New Git branch: `feature/excel-restructure`
> - Modified `app/pricing_calculator.py` with restructured `create_output_excel()` function
> - Excel output with new sheet structure
>
> **Estimated Effort**: Quick (single file modification, well-scoped change)
> **Parallel Execution**: NO - single sequential task
> **Critical Path**: Branch → Modify function → Manual verification

---

## Context

### Original Request
User wants to modify the Excel output structure. Current: Results sheet + Summary sheet + multiple "By X" sheets (By Resource Type, By Flavor Family, By DB Type, By Deployment, OSS Summary). Desired: Results sheet (unchanged) + per-resource-type sheets (ECS, Database, OSS) with merged summaries + Summary sheet in table format with totals.

### Interview Summary
**Key Discussions**:
- **Existing sheets**: Merge logically into per-type sheets
  - ECS sheet gets "By Flavor Family" content merged in
  - Database sheet gets "By DB Type" and "By Deployment" content merged in
  - OSS sheet gets "OSS Summary" content merged in
- **Summary format**: Table format with columns: Service, Count, Total Cost; rows: ECS, Database, OSS, GRAND TOTAL
- **Test strategy**: No automated tests - manual verification only
- **Branch name**: `feature/excel-restructure`

**Research Findings**:
- Excel library: `openpyxl` via `pandas.ExcelWriter`
- Main function: `create_output_excel()` in `app/pricing_calculator.py` lines 336-381
- Resource types: ECS, Database, OSS (case-insensitive)
- Filtering pattern: `df[df['Resource Type'].str.lower() == 'ecs']`

### Metis Review
**Identified Gaps** (addressed):
- **Layout order**: Results section first, then summary tables at bottom of each sheet (resolved: standard practice)
- **Count definition**: Sum of Quantity column (resolved: matches cost calculation needs)
- **Empty sheets**: Skip sheet creation if no items of that type (resolved: cleaner output)
- **Column consistency**: Keep all columns in per-type sheets (resolved: consistency)
- **Grand Total**: Include unmapped resources in grand total (resolved: current behavior preserved)
- **Sheet order**: Results → Summary → ECS → Database → OSS → Unmapped Resources (resolved: logical grouping)
- **OSS format**: All OSS-relevant fields merged into single sheet (resolved: user's merge request)

---

## Work Objectives

### Core Objective
Refactor `create_output_excel()` to produce cleaner Excel output with per-resource-type sheets and table-formatted summary.

### Concrete Deliverables
- Git branch `feature/excel-restructure` created from current branch
- `app/pricing_calculator.py` modified with new `create_output_excel()` implementation
- Excel output with sheet order: Results, Summary, ECS, Database, OSS, Unmapped Resources

### Definition of Done
- [ ] New branch created
- [ ] `create_output_excel()` produces sheets: Results (unchanged), Summary (table format), ECS, Database, OSS, Unmapped Resources
- [ ] Each per-type sheet contains: filtered results + relevant summary tables
- [ ] Summary sheet has: Service | Count | Total Cost table + GRAND TOTAL row
- [ ] Old "By X" sheets removed from output
- [ ] Manual verification: download Excel, inspect each sheet

### Must Have
- Results sheet unchanged (all columns, all rows)
- Summary sheet in table format with grand total
- Per-resource-type sheets with merged content
- Branch created before changes

### Must NOT Have (Guardrails)
- Do not modify data processing logic (only output formatting)
- Do not change column names or data types
- Do not add new dependencies
- Do not modify non-Excel parts of the codebase
- Do not create empty sheets (skip if no items of that type)

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: N/A (no automated tests)
- **Automated tests**: None (per user request)
- **Framework**: N/A
- **Agent-Executed QA**: YES - manual verification via Streamlit app

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Backend/Excel**: Use Bash (Streamlit + manual Excel inspection) — Run app, generate Excel, inspect structure
- **File verification**: Use Bash (git) — Verify branch created, verify changes committed

---

## Execution Strategy

### Parallel Execution Waves

> Single task - no parallel execution needed.

```
Wave 1 (Single Task):
└── Task 1: Restructure Excel output [quick]

Wave FINAL (After implementation — verification):
├── Task F1: Verify Excel structure (agent)
└── Task F2: Code review (agent)
-> Present results -> Get explicit user okay

Critical Path: Task 1 → F1 → F2 → user okay
```

### Dependency Matrix

- **1**: — 4, 1
- **F1**: 1 — F2, 1
- **F2**: F1 — user okay

### Agent Dispatch Summary

- **1**: **1** — Task 1 → `quick`
- **FINAL**: **2** — F1 → `unspecified-high`, F2 → `unspecified-low`

---

## TODOs

- [x] 1. Restructure Excel Output Sheets

  **What to do**:
  - Create new Git branch `feature/excel-restructure` from current branch
  - Modify `create_output_excel()` function in `app/pricing_calculator.py`
  - Implement new sheet structure:
    1. **Results sheet**: Keep unchanged (all columns, all rows)
    2. **Summary sheet**: Table format with columns `Service | Count | Total Cost`, rows for ECS/Database/OSS/GRAND TOTAL
    3. **ECS sheet**: ECS rows + Flavor Family summary table
    4. **Database sheet**: Database rows + DB Type summary table + Deployment summary table
    5. **OSS sheet**: OSS rows +OSS Summary table (storage/traffic/retrieval/requesquests)
    6. **Unmapped Resources sheet**: Keep unchanged (if exists)
  - Remove old sheets: "By Resource Type", "By Flavor Family", "By DB Type", "By Deployment", "OSS Summary"
  - Implement skip logic: don't create ECS/Database/OSS sheets if no items of that type

  **Must NOT do**:
  - Do not modify any data processing logic (only output formatting)
  - Do not change function signature or return type
  - Do not add new file dependencies
  - Do not modify columns or data transformation

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-file modification with clear scope, well-defined inputs/outputs
  - **Skills**: []
    - No special skills needed - standard pandas/openpyxlExcel writing

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: All verification tasks
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `app/pricing_calculator.py:336-381` - Current `create_output_excel()` implementation - follow this pattern for sheet creation
  - `app/pricing_calculator.py:312` - ECS filtering pattern: `df[df['Resource Type'].str.lower() == 'ecs']`
  - `app/pricing_calculator.py:317` - Database filtering pattern: `df[df['Resource Type'].str.lower() == 'database']`
  - `app/pricing_calculator.py:370` - OSS filtering pattern: `df[df['Resource Type'].str.lower() == 'oss']`
  - `app/pricing_calculator.py:346-348` - "By Resource Type" sheet creation - similar pattern for summary tables
  - `app/pricing_calculator.py:350-354` - "By Flavor Family" sheet creation - merge into ECS sheet
  - `app/pricing_calculator.py:356-360` - "By DB Type" and "By Deployment" sheet creation - merge into Database sheet
  - `app/pricing_calculator.py:362-371` - "OSS Summary" sheet creation - merge into OSS sheet

  **API/Type References** (contracts to implement against):
  - `pandas.ExcelWriter` - Use with `engine='openpyxl'`
  - `df.to_excel(writer, sheet_name='...')` - Standard sheet writing pattern

  **External References** (libraries and frameworks):
  - pandas ExcelWriter: https://pandas.pydata.org/docs/reference/api/pandas.ExcelWriter.html

  **WHY Each Reference Matters**:
  - `create_output_excel()` lines 336-381 - This is the ONLY function to modify; all changes happen here
  - Filtering patterns at lines 312, 317, 370 - Use exact same `.str.lower()` pattern for resource type filtering
  - Existing sheet creation patterns - Follow the same DataFrame writing approach for new sheets

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.

  - [ ] Branch `feature/excel-restructure` created
  - [ ] `to_excel_bytes()` in `huawei_pricing_app.py` still works (no signature change)
  - [ ] Excel output has exactly 6 sheets maximum (Results, Summary, ECS, Database, OSS, Unmapped Resources)
  - [ ] No old "By X" sheets in output
  - [ ] Each per-type sheet contains filtered results + summary table(s)- [ ] Summary sheet has table format with grand total row

  **QA Scenarios (MANDATORY — task is INCOMPLETE without these):**

  ```
  Scenario: Generate Excel with all resource types present
    Tool: Bash (Streamlit + Python inspection)
    Preconditions: Test file with ECS, Database, and OSS items uploaded
    Steps:
      1. Run streamlit app: `cd /mnt/c/Users/nabil/github/vm-database-mapper-HWC && streamlit run app/huawei_pricing_app.py --server.headless true`
      2. Upload test file with mixed resource types
      3. Generate Excel output
      4. Read Excel with pandas: `pd.ExcelFile(output_path).sheet_names`
      5. Assert sheet_names == ['Results', 'Summary', 'ECS', 'Database', 'OSS', 'Unmapped Resources']
    Expected Result: Excel has 6 sheets in correct order
    Failure Indicators: Missing sheets, extra sheets, wrong order
    Evidence: .sisyphus/evidence/task-1-all-types.xlsx

  Scenario: Generate Excel with only ECS items
    Tool: Bash (Python pandas)
    Preconditions: Test file with only ECS items
    Steps:
      1. Create DataFrame with only 'ECS' in Resource Type column
      2. Call `create_output_excel(df, summary, output)`
      3. Read Excel and check sheets: `pd.ExcelFile(output).sheet_names`
      4. Assert sheet_names == ['Results', 'Summary', 'ECS']
    Expected Result: Only Results, Summary, ECS sheets created (no Database, OSS sheets)
    Failure Indicators: Empty Database sheet created, empty OSS sheet created
    Evidence: .sisyphus/evidence/task-1-ecs-only.xlsx

  Scenario: Summary sheet has correct table format
    Tool: Bash (Python pandas)
    Preconditions: Excel generated with all resource types
    Steps:
      1. Read Summary sheet: `pd.read_excel(output, sheet_name='Summary')`
      2. Assert columns == ['Service', 'Count', 'Total Cost']
      3. Assert last row contains 'GRAND TOTAL'
      4. Assert Count values match sum of Quantity for each service
    Expected Result: Summary has correct columns and grand total row
    Failure Indicators: Wrong columns, missing grand total
    Evidence: .sisyphus/evidence/task-1-summary-check.png

  Scenario: Git branch verification
    Tool: Bash (git)
    Preconditions: Code changes complete
    Steps:
      1. Run `git branch --show-current`
      2. Assert output == 'feature/excel-restructure'
      3. Run `git log --oneline -1`
      4. Assert commit message follows convention
    Expected Result: On correct branch with commit
    Failure Indicators: Wrong branch name
    Evidence: .sisyphus/evidence/task-1-git-branch.txt
  ```

  **Evidence to Capture:**
  - [ ] task-1-all-types.xlsx - Excel with all resource types
  - [ ] task-1-ecs-only.xlsx - Excel with only ECS
  - [ ] task-1-summary-check.png - Summary sheet screenshot
  - [ ] task-1-git-branch.txt - Branch verification output

  **Commit**: YES (group: 1)
  - Message: `feat(excel): restructure output sheets to per-resource-type`
  - Files: `app/pricing_calculator.py`
  - Pre-commit: None (no automated tests)

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 2 verification agents run in PARALLEL. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Excel Structure Verification** — `unspecified-high`
  Run Streamlit app, generate Excel output, inspect structure. Verify: sheet order (Results, Summary, ECS, Database, OSS, Unmapped), each per-type sheet contains results + summary tables, Summary has table format with grand total. Check old "By X" sheets are removed.Save screenshots to `.sisyphus/evidence/final-qa/`.
  Output: `Sheets [N/N correct] | Structure [PASS/FAIL] | Format [PASS/FAIL] | VERDICT`

- [x] F2. **Code Quality Review** — `unspecified-low`
  Run code review on modified file. Check: no new dependencies, no data processing changes, function signature unchanged, pandas/openpyxl usage follows existing patterns. Verify branch exists and commits are clean.
  Output: `Branch [PASS/FAIL] | Code [PASS/FAIL] | Scope [PASS/FAIL] | VERDICT`

---

## Commit Strategy

- **1**: `feat(excel): restructure output sheets to per-resource-type` — app/pricing_calculator.py

---

## Success Criteria

### Verification Commands
```bash
git branch --show-current  # Expected: feature/excel-restructure
git diff main --stat      # Expected: 1 file changed
```

### Final Checklist
- [ ] Branch created and active
- [ ] Results sheet unchanged (all columns preserved)
- [ ] Summary sheet has table format with grand total
- [ ] ECS sheet exists and contains ECS results + Flavor Family summary
- [ ] Database sheet exists and contains Database results + DB Type + Deployment summaries
- [ ] OSS sheet exists and contains OSS results + OSS summary
- [ ] Old "By X" sheets removed from output
- [ ] No new dependencies added
- [ ] Code review passed