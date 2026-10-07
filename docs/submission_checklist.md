# BDS-06 Final Submission Checklist

Status key: **COMPLETE** = evidence exists and has been verified; **PARTIAL** = an artifact exists but evidence/scope is incomplete; **MISSING** = no artifact/evidence found; **NOT APPLICABLE** = not required for this project or not supplied by the institution.

## COMPLETED / EVIDENCE VERIFIED

| Item                                 | Status                                 | Evidence / remaining action                                                                                                   |
| ------------------------------------ | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Existing BDS-06 source code          | COMPLETE                               | `app/`, `scripts/`, `configs/`, `tests/`                                                                                      |
| Project README                       | COMPLETE                               | `README.md` states the verified one-hour point-forecast scope, local Docker path, and optional Render demo configuration.     |
| Dockerfile and Compose               | COMPLETE                               | `Dockerfile`, `docker-compose.yml`; built and run locally on 2026-10-01. Compose emits an ignored obsolete `version` warning. |
| Data/model artifacts                 | COMPLETE (reproducible synthetic)      | Generated from `scripts/generate_data.py` and `scripts/train_forecaster.py`; runtime artifacts are ignored by Git and regenerated for the Render image. |
| Automated tests                      | COMPLETE (local result)                | Final verification: `python -m pytest -q` passed with 178 tests and 1 existing Starlette/httpx deprecation warning.           |
| Final evidence matrix                | COMPLETE (documentation)               | `docs/bds06_evidence_matrix.md`; includes baseline audit and final status matrix.                                             |
| Model/system card                    | COMPLETE (documentation)               | `docs/model_system_card.md`; describes current supported model and limitations.                                               |
| Operator runbook                     | COMPLETE (documentation)               | `docs/runbook.md`; tested commands are distinguished from general guidance.                                                   |
| Administrator guide                  | COMPLETE (documentation)               | `docs/administrator_guide.md`; local dev/security caveats stated.                                                             |
| Stakeholder user guide               | COMPLETE (documentation)               | `docs/user_guide.md`; only actual Overview and Forecast Explorer workflows are described.                                     |
| Final report/blackbook-ready content | COMPLETE (Markdown and DOCX draft)     | `docs/final_report.md` and `Final_BDS06_Project_Report.docx`; institutional formatting, approval, and final review remain human work. |
| Presentation deck                    | COMPLETE (outline and PPTX draft)      | `docs/presentation_outline.md` and `BDS06_Final_Project_Presentation.pptx`; presentation rehearsal and final human review remain required. |
| Demo script                          | COMPLETE (script)                      | `docs/demo_script.md`; no recording or UI screenshot is claimed by the artifact.                                              |
| Release notes                        | COMPLETE                               | `docs/release_notes.md`; dated local environment evidence and limitations included.                                           |
| Render deployment configuration      | PARTIAL (ready to deploy)              | `render.yaml` and `Dockerfile.render`; a live service, successful container build, and public URL are not yet verified.        |
| Task 3.2                             | COMPLETE                               | `project-tasks/startup-mvp-tasklist.md`; Docker runtime/build/start/restart gates passed.                                     |
| Task 3.3                             | COMPLETE (documentation evidence only) | The capstone remains locked; this task is a post-capstone enhancement and final polish phase.                                 |

## HUMAN ACTION REQUIRED

| Item                                         | Status                   | Evidence / remaining action                                                                                                                                 |
| -------------------------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Environment template                         | PARTIAL                  | `.env.example`; development fallbacks only, not production secrets. Use distinct private local values for a demonstration.                                  |
| CI configuration                             | PARTIAL                  | `.github/workflows/ci.yml` exists; no remote GitHub Actions run evidence or repository metadata is available.                                               |
| Branch/PR/code-review evidence               | MISSING / NOT VERIFIABLE | Repository remote or PR metadata must be attached if the institution requires it.                                                                           |
| Security review                              | PARTIAL                  | `docs/security_review.md`; no vulnerability scanner run or institutional privacy approval is evidenced.                                                     |
| Evaluation dossier                           | PARTIAL                  | `docs/evaluation_dossier.md` and JSON/CSV artifacts; formal peak detection, repeated-run scenario stability, user study, and broad load test remain absent. |
| Demo recording / final video                 | MISSING / HUMAN ACTION   | Record and export the final local demo. Do not fabricate video or screenshots.                                                                              |
| Individual contribution evidence             | PARTIAL                  | `docs/contribution_evidence_template.md`; student identity, hours, and signatures must be filled by the student.                                            |
| Final viva rehearsal                         | MISSING / HUMAN ACTION   | Rehearse and record the viva Q&A; repository evidence alone cannot replace the live oral defence.                                                           |
| Institutional signatures / certificate pages | MISSING / HUMAN ACTION   | Complete the documentation required by the institution; not a repository artifact.                                                                          |
| Final print/export                           | MISSING / HUMAN ACTION   | Complete the required submission export and packaging as directed by the institution.                                                                       |
