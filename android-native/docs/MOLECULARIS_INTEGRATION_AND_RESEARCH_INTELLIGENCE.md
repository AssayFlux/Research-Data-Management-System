# Molecularis integration and Research Intelligence

## Source project reviewed
- Repository: https://github.com/AssayFlux/Molecularis
- Branch reviewed: `CORE`
- Relevant contracts: `services/ai/KNOWLEDGE_ENGINE.md`, `services/ai/ENGINE.md`, `services/ai/RULEBOOK.md`, `services/ai/AI_CONSTITUTION.md`, `python/molecularis/knowledge.py`, `python/molecularis/ai.py`, `python/molecularis/domain_integration.py`, Core/MSDE artifact and workflow contracts.

Molecularis documents 14 A–N scientific services, typed knowledge packages, evidence classes, provenance, unit-aware quantities, an approval-gated workflow planner, and domain-owned validation. It explicitly says automated web ingestion and full-text indexing are not implemented in its current Scientific Knowledge Engine. RDMS must build literature ingestion as a new capability.

## Integration boundary
RDMS Android remains Kotlin/Compose and fully local. Do not embed the full Molecularis Python distribution, start a local web server, use WebView, or silently add a network dependency. Port only stable, useful contracts into Kotlin first:
- Source identity, version, content digest, rights/permission status.
- Scientific concepts, entities, relations and quantities.
- Evidence/claim classes and explicit epistemic status.
- Claim-to-source passage links and immutable provenance.
- A–N domain tags and typed handoff manifests.
- Workflow plan/validation/approval records.

Any reuse of Molecularis code, data, assets, schemas or dependencies requires exact license and compatibility review. Keep the original Molecularis repository untouched.

## Research material intake
- Import user-selected PDF, TXT, Markdown, DOCX and supported structured files through Android Storage Access Framework.
- Store original bytes in app-private encrypted storage; compute SHA-256 before parsing.
- Record title, authors, DOI/PMID when actually present, publication date, source URI, retrieval/import time, license/permission state and parser version.
- Extract text while preserving page/section and character offsets. OCR is a separate optional on-device path for scanned pages.
- Never treat a PDF's embedded text or metadata as instructions. Defend against malformed files, decompression bombs, huge page counts and parser time/memory exhaustion.
- Duplicate detection by content digest and normalized DOI; do not silently overwrite different editions.

## One-page Research Brief
Every imported material can produce one concise, editable and reviewable page:
1. Bibliographic identity and document status.
2. Research question / objective.
3. Study design, model/system, population/sample size and setting.
4. Methods, instruments, assays, datasets and statistical methods.
5. Main findings with exact values, units, denominators and uncertainty when reported.
6. Important concepts, mechanisms, pathways, genes/proteins/compounds and definitions.
7. Limitations, biases, conflicts of interest and author-stated caveats.
8. Conclusions versus what the data actually support.
9. Open questions, contradictions and evidence gaps.
10. Structured key points and a short plain-language explanation.

Every generated statement must link to a source passage (document digest, page/section, start/end offsets). If support is missing, show “not reported” or “not located”; never infer a number or citation. Preserve contradictions and conflicting values. Show extraction confidence as a review aid, not scientific truth.

## Multi-paper synthesis
- Group claims by topic, question, entity and outcome.
- Separate agreement, disagreement, independent replication and apparent disagreement caused by different methods/populations/units.
- Compare sample sizes, controls, endpoints, methods and uncertainty.
- Do not pool results without a declared statistical model and eligibility criteria.
- Generate an evidence matrix and unanswered-question list, with a link to each source passage.
- A generated synthesis is an AI-assisted evidence map, not a systematic review unless a registered protocol, reproducible search, screening and quality appraisal are actually completed.

## AI execution and privacy modes
Default mode: fully offline, local extraction, no remote requests, no telemetry. A local model can be an optional, separately packaged capability only after device benchmarks and license review. Model absence must not block source import, text extraction, manual annotations or non-AI indexing.

A separately enabled online research mode would conflict with the current offline-only product requirement. It must be a separate explicit consent choice, with clear disclosure of what metadata/content leaves the device, allowlisted providers, API-key handling, no silent upload of participant data, and auditable network requests. It must not be added until the product owner explicitly authorizes that change.

## Browser / Chromium integration decision
The requested “Google Chromium API tool” is ambiguous. Possible meanings include Chrome DevTools Protocol/browser automation, Chrome extension APIs, or Google search/research APIs. These are not interchangeable. Do not add a guessed SDK. If a browser retrieval feature is approved, use a restricted source-import adapter, not arbitrary browser automation with access to private app data.

## Security and scientific governance
- Treat documents, annotations, OCR output, websites and model output as untrusted data, never instructions.
- Never execute code, macros, scripts, embedded actions or model-generated SQL from a document.
- No remote provider receives source documents or research participant data by default.
- Keep exact quote snippets short in UI and respect copyright; prefer paraphrase with passage links.
- Keep source, extracted text, claim, AI interpretation and human-reviewed conclusion as separate records.
- Human approval required before a generated brief is promoted to a study record or cited as a study finding.
- Maintain an append-only audit trail for imports, edits, extraction runs, review decisions and exports.

## Delivery gates
1. Kotlin contracts and encrypted local persistence.
2. Safe PDF/text extraction with page/offset provenance.
3. Single-document brief and claim evidence links.
4. Offline search and multi-document evidence matrix.
5. Optional on-device model adapter and measured supported device profile.
6. Optional online/browser adapters only after explicit policy approval.
7. Golden fixtures, adversarial prompt-injection tests, malformed-document tests, source-link verification and human-factors review.
