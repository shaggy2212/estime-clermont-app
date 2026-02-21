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

  async function debug(label) {
    const title = await page.title().catch(() => "");
    const body = ((await page.textContent("body").catch(() => "")) || "")
      .replace(/\s+/g, " ")
      .slice(0, 600);
    console.log(`=== DEBUG (${label}) ===`);
    console.log("TITLE:", title);
    console.log("BODY_SNIPPET:", body);
    console.log("=== END DEBUG ===");
  }

  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.waitForTim
