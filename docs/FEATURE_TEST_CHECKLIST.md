# LumaLab feature/update testing record (copy for each PR)

Use with [the SaaS baseline](CODERABBIT_SAAS_CHECKLIST.md). Copy this template into the PR description or a separate release record; keep this master reusable. Record PASS / FAIL / NOT TESTED / N/A plus evidence. Checked boxes require a completed result; N/A requires a reason. Do not paste credentials or private photographs.

## Change and scope

| Field | Fill in |
| --- | --- |
| Feature / PR / release | |
| Owner / reviewer / date | |
| Base commit / final head commit | |
| User problem and observable acceptance criteria | |
| Changed files, endpoints, schemas, DB objects, configuration | |
| Affected unchanged consumers / workflows | |
| Data flow: input -> validation -> processing -> storage -> response -> cleanup | |
| New trust boundaries, permissions, sensitive data or third parties | |
| Risk level and reasoning | |
| Active baseline control IDs; conditional sections and N/A reasons | |

## Acceptance and regression cases

Write explicit expected results before testing. For boundary values test below, at and above each threshold. For timing-sensitive changes force response reordering and concurrent calls rather than relying on chance.

| Case ID | Scenario / input / precondition | Expected result | Test level and location | Actual result / evidence / commit |
| --- | --- | --- | --- | --- |
| F-01 | Main successful feature flow | | | |
| F-02 | Minimum and maximum supported values | | | |
| F-03 | Invalid type/format/range/unknown property | | | |
| F-04 | Unauthorized or cross-session request | No unauthorized read/write/delete | | |
| F-05 | Session expires or is deleted during operation | Defined failure; no leak or stale success | | |
| F-06 | Duplicate requests / rapid double click | Bounded, correct behavior | | |
| F-07 | Concurrent requests / delayed old response | Latest intended state wins | | |
| F-08 | Network abort / disconnect / timeout | Cleanup and accurate UI state | | |
| F-09 | Resource exhaustion / 429 / 503 | Controlled rejection and recovery | | |
| F-10 | Dependency/storage failure mid-operation | Rollback; no corrupt or leaked data | | |
| F-11 | Existing workflow regression | Upload -> edit -> compare -> detail -> export -> delete still works | | |
| F-12 | Reset / undo / redo / image replacement | Complete correct state restored | | |
| F-13 | Browser/mobile/keyboard accessibility | Task remains usable | | |
| F-14 | Restart/deploy during use, if affected | Documented loss/recovery and cleanup | | |

## Select feature-specific checks

- [ ] Upload/input: malformed bytes, supported formats, animation rejection, streamed size limits, decoded pixel bounds, safe names, partial-write cleanup. Baseline FILE/API/LIMIT.
- [ ] Editing/rendering: neutral identity, all extrema, combined settings, versioned recipe, preview/export/detail parity, orientation/color/metadata, geometry/curve boundaries. Baseline IMG.
- [ ] Browser feature: complete snapshots, revision invalidation, A/B image races, cancellation, Blob cleanup, undo/redo, focus/touch/screen reader. Baseline UI.
- [ ] API change: request/response/error schema, status/headers, generated types, old/new compatibility, strict validation, authorization, privacy and route-specific limits. Baseline AUTH/API.
- [ ] Database change: parameterized SQL, constraints, transaction rollback, grants, query plans, real DB integration, migration from previous version and recovery. Baseline DB.
- [ ] Storage/lifecycle: concurrent access/delete/expiry/shutdown, exact byte accounting, disk full, permissions, orphan reclamation, retention bounds. Baseline FILE/LIFE/OPS.
- [ ] Performance change: repeatable before/after measurements, peak memory under mixed concurrency, long-running stability and image quality preservation. Baseline PERF/LIMIT.
- [ ] Dependency/deployment change: lockfile review, vulnerability and secret scans, real production-container smoke test, proxy/header/timeout validation, rollback. Baseline DEP.
- [ ] Account/team/library, billing, external AI/DataRobot or queue features: activate the applicable conditional baseline section before release.

## Performance and capacity evidence (when affected)

Record image dimensions/format/entropy, edit combination, hardware/container, network, concurrency, run count and cold/warm conditions. Set budgets before comparing; leave unmeasured cells NOT TESTED.

| Metric | Approved budget | Before | After | Evidence |
| --- | --- | --- | --- | --- |
| Upload-to-ready latency | | | | |
| Preview latency / slider feedback | | | | |
| Enhancement latency | | | | |
| Full-resolution detail/export latency | | | | |
| Peak server RSS / CPU | | | | |
| Peak browser memory / long tasks | | | | |
| Temp bytes / open files / session count after soak | | | | |
| Throughput / rejection rate / health latency at load | | | | |
| Recovery time after overload/fault | | | | |

## Control coverage and findings

Create one row per applicable baseline control, not just per section. Include inherited controls whose behavior can change indirectly. Link the actual test or trace; a reviewer opinion alone cannot verify runtime capacity or production settings.

| Baseline control ID | PASS / FAIL / NOT TESTED / N/A | Evidence or N/A reason | Finding / owner |
| --- | --- | --- | --- |
| | | | |

Use the baseline finding format for each issue. Record what CodeRabbit reviewed separately from what test tools executed.

| Finding | Severity / confidence | Fix or accepted risk | Owner / deadline / exception expiry | Final-commit retest |
| --- | --- | --- | --- | --- |
| | | | | |

## Release decision

- [ ] CodeRabbit reviewed the intended final commit with the baseline and this completed record; record scope and any missing context.
- [ ] Applicable backend/unit/build/contracts/browser checks pass with linked output.
- [ ] New failure modes and fixed defects have meaningful regression cases.
- [ ] Applicable security scans and real PostgreSQL/container/infrastructure checks have evidence.
- [ ] Relevant load, failure, retention and image-quality checks pass against approved budgets.
- [ ] No unresolved blocking issue or untested high-risk control; exceptions have explicit decision, owner, compensating controls and expiry.
- [ ] Docs, contracts, limits, monitoring and operational runbooks match the delivered behavior.
- [ ] Rollback/roll-forward, migration compatibility and session-disruption behavior are documented.
- [ ] Post-deploy synthetic smoke check and alert observation have an assigned owner.

Decision: RELEASE / HOLD

Decision owner and date:

Remaining risks and accepted exceptions:

Deployed artifact/commit and post-deploy evidence:

New reusable regression case or baseline improvement learned from this update:
