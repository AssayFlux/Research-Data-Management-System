# Chrome extension integration decision

User selected option 3: Chrome extension APIs.

The prototype is located at `/browser-extension`. It uses Manifest V3, `activeTab`, `scripting`, and `downloads` to capture a researcher-opened page after an explicit click. It exports a local `.rdms-capture.json` file. No host permissions or remote API calls are requested.

This preserves the Android app's offline-only policy: capture occurs on desktop Chrome, then the user transfers the file to the Android device for import. It is not a Chrome extension running inside Android Chrome (which does not provide the standard desktop Chrome extension runtime).

Remaining implementation:
- Add strict schema/version validation and safe size limits to Android capture importer.
- Encrypt the captured source package and index metadata in Room.
- Preserve original URL, capture timestamp, text hash, selection and content provenance.
- Parse DOI/PMID/citation metadata cautiously; never invent missing bibliographic fields.
- Build source passage offsets and link generated claims to exact passage locations.
- Add PDF file import separately for original layout and page-number citations.
- Test on dynamic, multi-frame, paywalled, very long, malformed and hostile pages.
- Document content licensing and institutional review responsibilities.

Do not silently add an online API or background crawler. Any future remote literature search requires explicit product approval and a separate privacy mode.
