# RDMS Research Capture — Chrome extension (early prototype)

This is a Manifest V3 desktop Chrome extension companion for RDMS Android.

## What it does
- The researcher navigates to a research webpage themselves.
- The researcher clicks the extension and explicitly chooses to capture.
- The extension reads the active tab using `activeTab` + `scripting`.
- It extracts page title, URL, selected text, readable article/main text and selected bibliographic metadata.
- It downloads a JSON evidence package that can be moved to the Android device and imported offline.

## Privacy / security
- No host-wide permissions; only the active tab after a user gesture.
- No remote API, analytics, telemetry, account login or background scraping.
- The extension does not bypass paywalls, authentication, robots restrictions or technical access controls.
- A page's content is untrusted input, not instructions for an AI agent.
- Captured content may be incomplete or copyrighted. Respect site terms, licenses and institutional policy; preserve source URLs and verify quotations.
- The capture file may contain sensitive content. Store and transfer it securely.

## Install for development
1. Open `chrome://extensions` in desktop Google Chrome.
2. Enable Developer mode.
3. Choose **Load unpacked** and select this directory.
4. Open a page you are permitted to capture, then click the extension.
5. Choose a destination for the `.rdms-capture.json` file.
6. Transfer it to the Android device and import it through RDMS.

## Current limitations
- Prototype only; not yet packaged or store-published.
- It captures readable text, not original PDF bytes, page layout, figures, tables, supplementary files or reliable PDF page numbers.
- Some sites render content inside frames or canvas, block extraction, or expose only partial text.
- DOI/author/date metadata is best-effort and must be verified.
- Android RDMS does not yet have the JSON capture importer or the completed evidence extraction pipeline.
- It does not perform AI summarization itself.

## Offline contract
The Android app remains offline-only. The extension is a separate desktop browser companion used to gather user-selected source material. The downloaded file is manually transferred/imported; the extension does not connect to the phone or send anything to a server.
