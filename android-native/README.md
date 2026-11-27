# RDMS Native Android — Beta

This directory is the isolated native Android implementation track. The legacy Flask/PWA application and its database remain untouched on `main`.

## Product requirements
- Native Kotlin + Jetpack Compose; no WebView, Flask runtime, or website assets.
- Fully offline on one Android device. No cloud, sync, telemetry, ads, or network calls.
- No Android `INTERNET` permission.
- Encrypted local database and private attachment storage.
- BiometricPrompt authorization backed by Android Keystore, with a tested recovery path.
- Encrypted export/import backups usable through Android Storage Access Framework and USB OTG.
- Preserve existing research workflows, permissions, audit history, statistical definitions, and attachments.

## Beta status
**Scaffold only — not feature complete and not safe for production research data.** The current app module establishes a native Compose launcher and an offline-only manifest. It does not yet implement the RDMS feature set, encrypted Room/SQLCipher database initialization, biometric gate, migration, or backup/restore.

## Build
Open this directory in Android Studio (JDK 17, Android SDK 35) and sync Gradle. Build the debug APK with:

```bash
gradle :app:assembleDebug
```

## Required implementation gates
1. Inventory every legacy route, template, schema object, permission check, calculation, export, and file workflow.
2. Define a versioned Room schema and encrypted database key lifecycle. Never ship a hard-coded database key.
3. Implement biometric unlock and an independently tested recovery mechanism; biometric templates remain under Android OS control.
4. Port every feature and statistical algorithm, with golden-reference tests against the legacy Python implementation.
5. Build a read-only legacy data importer and validate counts, foreign keys, histories, and attachment hashes before activation.
6. Implement authenticated encrypted backup/restore. A failed restore must leave the active database unchanged.
7. Run unit, instrumentation, migration, offline-network, security, and device compatibility tests before calling this a release.

## Data protection notes
- Keep production data in app-private storage; exclude it from device cloud backup.
- Do not log participant identifiers or research values.
- Do not place sensitive values in QR payloads; use opaque local references.
- Deny study access by default unless an explicit assignment grants it.
- A recovery secret must be user-controlled and never embedded in source code.
