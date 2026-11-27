const button = document.getElementById("capture");
const status = document.getElementById("status");

button.addEventListener("click", async () => {
  button.disabled = true;
  status.textContent = "Reading the active tab…";
  try {
    const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (!tab?.id || !/^https?:/.test(tab.url || "")) {
      throw new Error("Open a normal research webpage before capturing.");
    }
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const meta = (names) => {
          for (const name of names) {
            const node = document.querySelector(
              `meta[name="${name}"],meta[property="${name}"]`
            );
            if (node?.content?.trim()) return node.content.trim();
          }
          return null;
        };
        const article = document.querySelector("article") ||
          document.querySelector("main") || document.body;
        const text = (article?.innerText || document.body?.innerText || "").trim();
        const selection = window.getSelection()?.toString()?.trim() || "";
        return {
          schema: "rdms.web-capture.v1",
          capturedAt: new Date().toISOString(),
          source: {
            url: location.href,
            title: document.title || "",
            siteName: meta(["og:site_name", "application-name"]),
            description: meta(["description", "og:description"]),
            authors: meta(["author", "citation_author"]),
            publishedDate: meta(["article:published_time", "date", "citation_publication_date"]),
            doi: meta(["citation_doi", "dc.identifier"])
          },
          selectedText: selection,
          pageText: text,
          captureNotes: [
            "Captured from the page currently displayed in the user's browser.",
            "This content may be incomplete, paywalled, dynamically rendered, or subject to copyright.",
            "Verify bibliographic details and source passages before citing."
          ]
        };
      }
    });
    const payload = result?.result;
    if (!payload?.pageText) throw new Error("No readable page text was found.");
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const objectUrl = URL.createObjectURL(blob);
    const safeName = (payload.source.title || "research-capture")
      .replace(/[^a-z0-9-_]+/gi, "-").replace(/^-+|-+$/g, "").slice(0, 70) || "research-capture";
    await chrome.downloads.download({
      url: objectUrl,
      filename: `RDMS-Captures/${safeName}.rdms-capture.json`,
      saveAs: true
    });
    setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    status.textContent = "Capture saved. Import the JSON file into RDMS.";
  } catch (error) {
    status.textContent = error?.message || "Capture failed.";
  } finally {
    button.disabled = false;
  }
});
