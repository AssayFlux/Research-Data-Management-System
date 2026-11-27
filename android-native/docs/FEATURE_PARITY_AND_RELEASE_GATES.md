# Legacy-to-native parity register

This register is intentionally conservative: a feature is not complete until its native implementation and parity tests exist.

| Area | Required native behavior | Status |
|---|---|---|
| Authentication | Local accounts, lock/unlock, role enforcement, recovery | Not implemented |
| Studies | Create/edit/archive/freeze, explicit membership and permissions | Not implemented |
| Participants | Profiles, classifications, consent, participant history | Not implemented |
| Parameters | Categories, units, ranges, validation | Not implemented |
| Forms | Form builder, field rules, versioning | Not implemented |
| Research records | Entry, missing states, history, locking | Not implemented |
| Attachments | Private encrypted file storage and integrity checks | Not implemented |
| Biospecimens | Inventory, collection, processing, tracking | Not implemented |
| Follow-up visits | Scheduling, visit forms, completion/history | Not implemented |
| Quality control | Checks, exceptions, alerts | Not implemented |
| Adverse events | Capture, severity, follow-up, audit | Not implemented |
| Statistics | Descriptive, normality, tests, correlation, regression, diagnostics, forecasting, sample size | Not implemented |
| Recruitment | Recruitment tracking and status workflows | Not implemented |
| Reliability | Inter-rater and reliability analysis | Not implemented |
| Longitudinal analysis | Repeated-measures and longitudinal workflows | Not implemented |
| QR | QR generation/scanning using opaque participant references only | Not implemented |
| Reports | Native PDF, CSV, XLSX generation | Not implemented |
| Administration | Users, roles, assignments, audit trail | Not implemented |
| Migration | Read-only legacy import with reconciliation | Not implemented |
| Backup/restore | Password-protected encrypted archive, USB/SAF transfer, atomic restore | Not implemented |


| Research materials | Encrypted PDF/TXT/DOCX import, parsing, OCR and source provenance | Partial: TXT/Markdown parser contracts only |
| Research Intelligence | Passage-linked extraction, one-page brief, review workflow, multi-paper synthesis | Partial: contracts and brief UI; no model or PDF/DOCX parser |
| Molecularis integration | Kotlin scientific knowledge/evidence contracts and A–N adapter boundary | Partial: design and evidence-first claim contracts |
| Browser / Chromium research source | Approved browser/search adapter with consent and source provenance | Not specified; awaiting exact API choice and online-mode approval |

## Audit findings to carry into implementation
- Reconcile the QR endpoint names registered by the QR router with the central study-access allowlist; add authorization tests for every QR route.
- Replace QR payloads containing participant attributes or measurements with random opaque local references.
- Remove the legacy compatibility behavior that treats users with zero study assignments as unrestricted; authorization must deny by default.
- The legacy SQLite database is not encrypted at rest; migrated Android storage must use a vetted SQLCipher integration and Android Keystore-backed key management.
- Reproduce and test legacy backup semantics before designing a compatible importer.
- Port statistical formulas and conventions explicitly; compare Kotlin results to fixed Python/SciPy reference datasets, including missing values, small samples, and degenerate inputs.

## Release acceptance checklist
- [ ] Every row above implemented and reviewed.
- [ ] No website, Flask, WebView, server, cloud, or sync dependency.
- [ ] Manifest has no INTERNET permission; runtime network inspection confirms no outbound traffic.
- [ ] Encrypted database and attachment encryption verified on-device.
- [ ] Biometric unlock and recovery path tested, including biometric enrollment changes.
- [ ] Explicit study assignment required for every protected operation.
- [ ] Legacy import reconciles row counts, relationships, audit/history, and attachment hashes.
- [ ] Statistical golden tests pass within documented tolerances.
- [ ] PDF/CSV/XLSX exports work in airplane mode.
- [ ] Encrypted backup restores on a second compatible device without transferring keys in plaintext.
- [ ] Failed import/restore leaves active data unchanged.
- [ ] Instrumentation and supported-device tests pass.
- [ ] Beta APK and signed release APK built and checksums recorded.

Do not mark a row complete based only on a screen existing. Require persistence, authorization, error handling, audit behavior, and automated tests.
