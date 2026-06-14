# Test Coverage Improvement Issues

This backlog is based on real local coverage artifacts in this checkout:

- Frontend report: `superset-frontend/coverage/coverage-summary.json`
  - Total line coverage: **68.65%** (`39,796 / 57,961` lines)
  - Total branch coverage: **61.33%** (`26,007 / 42,403` branches)
- Backend report: `.devin-automation/backend-coverage-unit.json`
  - Total line coverage: **63.22%** (`50,710 / 75,758` lines)
  - Total branch coverage: **47.50%** (`8,505 / 17,906` branches)

---

## 1. Add RTL tests for DatabaseList semantic-layer and CRUD flows

**Labels:** `devin-remediate`, `coverage-improvement`, `test-gap`, `frontend`

**Coverage data:**

- File: `superset-frontend/src/pages/DatabaseList/index.tsx`
- Lines: **0.00%** (`0 / 183`)
- Branches: **0.00%** (`0 / 130`)
- Functions: **0.00%** (`0 / 70`)

**Why this matters:**

`DatabaseList` is a high-traffic admin/user page that handles database listing, semantic-layer connection listing, modal entry points, delete/export actions, permission sync behavior, and feature-flag-dependent rendering.

**Proposed remediation:**

Add focused Jest + React Testing Library tests for the page using mocks for `useListViewResource`, `SupersetClient`, feature flags, and toast callbacks.

**Acceptance criteria:**

- Cover the default database-list path when semantic layers are disabled.
- Cover the combined semantic-layer connections fetch path when the semantic layer feature flag is enabled.
- Cover at least one fetch/error path that raises a danger toast.
- Cover one user action path, such as opening a create/upload modal or refreshing after creation.
- Avoid adding TypeScript `any` types in new tests.

---

## 2. Add embedded entrypoint tests for guest auth and data-mask behavior

**Labels:** `devin-remediate`, `coverage-improvement`, `test-gap`, `frontend`

**Coverage data:**

- File: `superset-frontend/src/embedded/index.tsx`
- Lines: **0.00%** (`0 / 98`)
- Branches: **0.00%** (`0 / 28`)
- Functions: **0.00%** (`0 / 18`)

**Why this matters:**

The embedded entrypoint initializes embedded dashboards, guest-user permissions, unauthorized handling, iframe-only behavior, and data-mask event emission to the parent application.

**Proposed remediation:**

Add focused Jest tests with mocked bootstrap data, Redux store, `makeApi`, `Switchboard`, and setup functions.

**Acceptance criteria:**

- Cover the non-iframe failure message path.
- Cover successful startup after `/api/v1/me/roles/` returns user/role data.
- Cover guest unauthorized handling and verify duplicate danger toasts are suppressed.
- Cover data-mask emission through `Switchboard.emit` when `emitDataMasks` is enabled.
- Keep tests deterministic and avoid real browser/network dependencies.

---

## 3. Add tests for API key list and create modal flows

**Labels:** `devin-remediate`, `coverage-improvement`, `test-gap`, `frontend`

**Coverage data:**

- File: `superset-frontend/src/features/apiKeys/ApiKeyList.tsx`
  - Lines: **0.00%** (`0 / 45`)
  - Branches: **0.00%** (`0 / 23`)
  - Functions: **0.00%** (`0 / 14`)
- File: `superset-frontend/src/features/apiKeys/ApiKeyCreateModal.tsx`
  - Lines: **0.00%** (`0 / 38`)
  - Branches: **0.00%** (`0 / 14`)
  - Functions: **0.00%** (`0 / 8`)

**Why this matters:**

These components manage scoped programmatic access. They include important success, failure, copy, and revoke states that should not regress silently.

**Proposed remediation:**

Add Jest + React Testing Library tests for API key listing, creation, copying, and revocation using mocked `SupersetClient`, toast hooks, modal confirmation, and clipboard APIs.

**Acceptance criteria:**

- Cover successful API key fetch and table rendering.
- Cover fetch failure and danger toast behavior.
- Cover revoke confirmation success and failure paths.
- Cover create modal submit success and missing-key response handling.
- Cover copy-to-clipboard success and failure behavior.

---

## 4. Add QueryHistoryList tests for preview and SQL rendering paths

**Labels:** `devin-remediate`, `coverage-improvement`, `test-gap`, `frontend`

**Coverage data:**

- File: `superset-frontend/src/pages/QueryHistoryList/index.tsx`
- Lines: **0.00%** (`0 / 71`)
- Branches: **0.00%** (`0 / 36`)
- Functions: **0.00%** (`0 / 28`)

**Why this matters:**

Query history is a user-facing workflow that renders SQL previews, query states, filters, owners, and navigation/action behavior.

**Proposed remediation:**

Add focused Jest + React Testing Library tests by mocking `useListViewResource`, `SupersetClient`, router history, and SQL highlighter preload behavior.

**Acceptance criteria:**

- Cover list rendering with representative successful, failed, and running query states.
- Cover SQL preview fetch success and modal display.
- Cover SQL preview failure and danger toast behavior.
- Cover at least one link/navigation or row action behavior.
- Avoid brittle snapshot-only tests.

---

## 5. Add transformProps tests for ECharts Histogram chart

**Labels:** `devin-remediate`, `coverage-improvement`, `test-gap`, `frontend`

**Coverage data:**

- File: `superset-frontend/plugins/plugin-chart-echarts/src/Histogram/transformProps.ts`
- Lines: **0.00%** (`0 / 50`)
- Branches: **0.00%** (`0 / 18`)
- Functions: **0.00%** (`0 / 18`)

**Why this matters:**

This is a high-leverage pure transform target. It can be tested without browser rendering and protects chart behavior around grouping, normalization, labels, tooltips, and legend state.

**Proposed remediation:**

Add unit tests for `transformProps` covering grouped and ungrouped histogram data, legend defaults, tooltip rows, axis formatting, normalized mode, and show-value labels.

**Acceptance criteria:**

- Cover ungrouped histogram series construction.
- Cover grouped histogram series names and color selection.
- Cover tooltip formatting with totals and percentage rows when not normalized.
- Cover normalized behavior where percentage rows are omitted.
- Cover legend state initialization for empty `legendState`.

---

## 6. Add backend unit tests for MCP retry utilities

**Labels:** `devin-remediate`, `coverage-improvement`, `test-gap`, `backend`

**Coverage data:**

- File: `superset/mcp_service/utils/retry_utils.py`
- Lines: **0.00%** (`0 / 113`)
- Branches: **0.00%** (`0 / 20`)

**Why this matters:**

Retry behavior affects MCP service reliability and error handling. This file is a good unit-test target because retry timing and exceptions can be tested deterministically with mocks.

**Proposed remediation:**

Add pytest coverage for synchronous and asynchronous retry decorators, backoff calculation, non-retryable exceptions, final failure behavior, logging, and HTTP retry classification behavior where applicable.

**Acceptance criteria:**

- Cover `exponential_backoff` with and without jitter, including max-delay clamping.
- Cover `retry_on_exception` success-after-retry and exhausted-retry paths without real sleeps.
- Cover non-retryable exception behavior.
- Cover `async_retry_on_exception` success and failure paths.
- Cover HTTP exception retryability helpers if present in the module.

---

## 7. Add backend tests for ResetSupersetCommand validation and exclusions

**Labels:** `devin-remediate`, `coverage-improvement`, `test-gap`, `backend`

**Coverage data:**

- File: `superset/commands/security/reset.py`
- Lines: **0.00%** (`0 / 50`)
- Branches: **0.00%** (`0 / 16`)

**Why this matters:**

`ResetSupersetCommand` performs destructive reset behavior. It should have focused tests around validation, default exclusions, custom exclusions, preserved admin users, logging, and commit behavior.

**Proposed remediation:**

Add pytest unit tests using mocks/fakes for `db.session`, `security_manager`, user/role models, and affected model queries. Avoid deleting real application state.

**Acceptance criteria:**

- Cover validation failure when `confirm` is false.
- Cover validation failure when the invoking user is missing or inactive.
- Cover default and custom excluded users/roles.
- Cover that admin users are preserved even when returned by the query.
- Cover that reset creates a `Factory Reset` log entry and commits.

---

## 8. Add backend tests for tag SQLAlchemy listener registration

**Labels:** `devin-remediate`, `coverage-improvement`, `test-gap`, `backend`

**Coverage data:**

- File: `superset/tags/core.py`
- Lines: **4.55%** (`2 / 44`)
- Branches: **100.00%** (`0 / 0`, no measured branches)

**Why this matters:**

This module registers and clears SQLAlchemy event listeners for datasets, charts, dashboards, favorite stars, and saved queries. Regressions could break automatic tag updates.

**Proposed remediation:**

Add pytest tests that monkeypatch `sqlalchemy.event.listen` and `sqlalchemy.event.remove`, then assert the expected model/updater/event combinations are registered and cleared.

**Acceptance criteria:**

- Cover `register_sqla_event_listeners`.
- Cover `clear_sqla_event_listeners`.
- Assert listener registration/removal for dataset, chart, dashboard, favorite-star, and saved-query updaters.
- Keep tests isolated from real SQLAlchemy global listener state.

---

## 9. Add backend unit tests for MCP WebDriverPool lifecycle behavior

**Labels:** `devin-remediate`, `coverage-improvement`, `test-gap`, `backend`

**Coverage data:**

- File: `superset/mcp_service/screenshot/webdriver_pool.py`
- Lines: **0.00%** (`0 / 222`)
- Branches: **0.00%** (`0 / 52`)

**Why this matters:**

`WebDriverPool` manages pooled screenshot browser instances, health checks, timeouts, eviction, and cleanup. This is operationally sensitive code with many branch-heavy lifecycle paths.

**Proposed remediation:**

Add unit tests with fake WebDriver objects and mocked `WebDriverSelenium`, `time.time`, and queue behavior. Avoid launching real browsers.

**Acceptance criteria:**

- Cover pool stats initialization and active/idle counts.
- Cover driver validity checks for age, usage count, idle timeout, and unhealthy state.
- Cover health-check success and `WebDriverException` failure behavior.
- Cover driver creation timeout/error cleanup behavior with mocks.
- Cover borrow/return/eviction paths without real Selenium sessions.

---

## 10. Add backend tests for dashboard update tab/native-filter diff behavior

**Labels:** `devin-remediate`, `coverage-improvement`, `test-gap`, `backend`

**Coverage data:**

- File: `superset/commands/dashboard/update.py`
- Lines: **20.20%** (`40 / 158`)
- Branches: **0.00%** (`0 / 40`)

**Why this matters:**

`UpdateDashboardCommand` contains important validation and side-effect behavior, including slug uniqueness, owners/roles/tags validation, dashboard tab removal, report deactivation, and native filter diff handling.

**Proposed remediation:**

Add focused pytest unit tests for command validation and diff-processing behavior with mocked DAOs, security manager, and report schedules.

**Acceptance criteria:**

- Cover not-found, forbidden, duplicate-slug, owner, role, and tag validation paths.
- Cover `position_json` reserialization behavior.
- Cover deleted-tab detection and report deactivation.
- Cover deleted native-filter ID detection from `json_metadata`.
- Cover email notification behavior through a mocked SMTP sender.
