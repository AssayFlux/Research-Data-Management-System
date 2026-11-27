# RDMS Native Android — Early Beta Foundation

This directory is an isolated native Android development track. The legacy Flask/PWA application and its database remain untouched on `main`.

## Product target
- Native Kotlin + Jetpack Compose; no WebView or embedded website.
- Fully offline, single-device operation; no cloud, sync, telemetry, ads, or network calls.
- No Android `INTERNET` permission.
- Encrypted local database and attachment storage.
- Android BiometricPrompt authorization; biometric templates remain under OS control.
- Encrypted backup/import with password-based cross-device recovery and USB/SAF support.
- Full parity with existing RDMS workflows, permissions, audit history, statistical behavior, and attachments.

## Current implementation status — NOT COMPLETE
This is an early engineering foundation, **not a usable RDMS beta and not approved for real research data**.

Implemented in source:
- Native Compose launcher.
- Initial biometric/device-credential prompt screen.
- Secure-window flag to block screenshots/recents previews.
- Initial Room entities/DAO for studies, participants, and audit events.
- SQLCipher Room database factory using an Android Keystore-wrapped random database passphrase.
- Android Keystore AES key helper and AES-GCM authenticated payload/streaming attachment primitives.
- Explicit study access policy with deny-by-default behavior and unit tests.
- Initial encrypted backup envelope primitive.
- GitHub Actions workflow intended to compile the debug APK and run unit tests.

Not implemented or not verified:
- Full feature screens and workflows; most of the legacy RDMS is still absent.
- Complete Room schema, migrations, and enforced foreign-key/authorization boundaries.
- A biometric-bound key lifecycle, recovery credential, and safe key rotation.
- Production-safe encrypted backup archive, password-derived cross-device key, SAF/USB export/import, and atomic restore.
- Legacy database and attachment importer with reconciliation.
- Statistical algorithm port and golden-reference tests.
- Native PDF, CSV, and XLSX exports.
- End-to-end, instrumentation, security, offline-network, and device testing.
- Successful Gradle build and installable APK artifact.

## Build
Open this directory in Android Studio with JDK 17 and Android SDK 35. The intended commands are:

```bash
gradle :app:assembleDebug
gradle :app:testDebugUnitTest
```

A root-level GitHub Actions workflow at `.github/workflows/android-native.yml` is configured to run these commands on pushes/PRs to `android-native`. A green CI result is required before treating this scaffold as build-verified.

## Security caveats
- Do not enter real participant or research data in this build.
- The current biometric screen is a UI gate, not yet a complete cryptographic authorization boundary. The SQLCipher key is Keystore-wrapped but not yet bound to successful biometric authentication.
- Cross-device recovery is not available yet; a Keystore key is device-bound.
- The backup envelope primitive is not a complete backup/restore workflow.
- Streaming GCM decryption must read to EOF and handle authentication failures before any restored file is committed.
- Keep production data in app-private storage; exclude it from Android cloud backup.
- Do not log participant identifiers or research values.
- QR payloads must contain opaque local references only.
- Deny study access by default unless an explicit assignment grants it.

## Release acceptance
See [FEATURE_PARITY_AND_RELEASE_GATES.md](docs/FEATURE_PARITY_AND_RELEASE_GATES.md). No feature is complete merely because a screen or data class exists; persistence, authorization, audit behavior, failure handling, and automated tests are required.
