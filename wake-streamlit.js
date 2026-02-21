const { chromium } = require("playwright");

(async () => {
  const url = process.env.STREAMLIT_URL;
  if (!url) throw new Error("Missing STREAMLIT_URL env var");

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 720 },
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
  });

  // Helper: dump debug
  async function debug(label) {
    const title = await page.title().catch(() => "");
    const body = (await page.textContent("body").catch(() => "")) || "";
    console.log(`\n=== DEBUG (${label}) ===`);
    console.log("TITLE:", title);
    console.log("BODY_SNIPPET:", body.slice(0, 600).replace(/\s+/g, " "));
    console.log("=== END DEBUG ===\n");
  }

  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.waitForTimeout(1500);

  // Détection du mode sleep
  const bodyText1 = (await page.textContent("body").catch(() => "")) || "";
  const isSleep = /zzzz|get this app back up|back up/i.test(bodyText1);

  if (isSleep) {
    console.log("Sleep screen detected 💤");
    await debug("sleep-detected");

    // Clique bouton wake (plusieurs variantes)
    const wakeCandidates = [
      page.getByRole("button", { name: /yes,?\s*get this app back up/i }),
      page.getByRole("button", { name: /get this app back up/i }),
      page.locator("button:has-text('get this app back up')"),
      page.locator("button:has-text('Yes, get this app back up')"),
      page.getByRole("button", { name: /wake up/i }
