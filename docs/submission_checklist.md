# BDS-06 Final Submission Checklist

Status key: **COMPLETE** = evidence exists and has been verified; **PARTIAL** = an artifact exists but evidence/scope is incomplete; **MISSING** = no artifact/evidence found; **NOT APPLICABLE** = not required for this project or not supplied by the institution.

| Item | Status | Evidence / remaining action |
| --- | --- | --- |
| Existing BDS-06 source code | COMPLETE | `app/`, `scripts/`, `configs/`, `tests/` |
| Project README | PARTIAL | `README.md`; update claims to current one-hour point forecast and current Docker evidence. |
| Dockerfile and Compose | COMPLETE | `Dockerfile`, `docker-compose.yml`; built and run locally on 2026-10-01. Compose emits an ignored obsolete `version` warning. |
| Environment template | PARTIAL | `.env.example`; development fallbacks only, not production secrets. Use distinct private local values for a demonstration. |
| Data/model artifacts | COMPLETE (synthetic) | `data/raw`, `data/processed`, `experiments/xgboost`; synthetic provenance documented. |
| Automated tests | COMPLETE (local result) | Latest recorded suite: 176 passed, 0 failed, 643 warnings; existing `coverage.xml` reports an 86.48% line rate and was not regenerated during this handoff. |
| CI configuration | PARTIAL | `.github/workflows/ci.yml` exists; no remote GitHub Actions run evidence or repository metadata is available. |
| Branch/PR/code-review evidence | MISSING / NOT VERIFIABLE | Workspace is not a Git repository. Attach actual remote records if they exist. |
| Security review | PARTIAL | `docs/security_review.md`; update Docker runtime facts; no vulnerability scanner run or institutional privacy approval is evidenced. |
| Evaluation dossier | PARTIAL | `docs/evaluation_dossier.md` and JSON/CSV artifacts; formal peak detection, repeated-run scenario stability, user study, and broad load test remain absent. |
| Final evidence matrix | COMPLETE (documentation) | `docs/bds06_evidence_matrix.md`; includes baseline audit and final status matrix. |
| Model/system card | COMPLETE (documentation) | `docs/model_system_card.md`; describes current supported model and limitations. |
| Operator runbook | COMPLETE (documentation) | `docs/runbook.md`; tested commands are distinguished from general guidance. |
| Administrator guide | COMPLETE (documentation) | `docs/administrator_guide.md`; local dev/security caveats stated. |
| Stakeholder user guide | COMPLETE (documentation) | `docs/user_guide.md`; only actual Overview and Forecast Explorer workflows are described. |
| Final report/blackbook-ready content | COMPLETE (Markdown content) | `docs/final_report.md`; Word/PDF typesetting and institutional formatting remain human/toolchain work. |
| Presentation deck content | COMPLETE (slide content) | `docs/presentation_deck.md`; actual slide design/rehearsal/export remains human work. |
| Demo script/video plan | COMPLETE (script) / MISSING (recording) | `docs/demo_script.md`; no actual recording or UI screenshot is present. |
| Individual contribution evidence | PARTIAL | `docs/contribution_evidence_template.md`; student identity, actual hours, owned tasks, signatures, and any remote Git proof must be filled by the student. |
| Release notes | COMPLETE | `docs/release_notes.md`; dated local environment evidence and limitations included. |
| Task 3.2 | COMPLETE | `project-tasks/startup-mvp-tasklist.md`; Docker runtime/build/start/restart gates passed. |
| Task 3.3 | PENDING FINAL REVIEW | Do not mark complete until documentation consistency is checked and Reality Checker approves the evidence; keep human submission gaps separate. |
| Final video, actual contribution hours, viva rehearsal | MISSING / HUMAN ACTION | Complete and attach institution-required evidence; do not fabricate it. |
