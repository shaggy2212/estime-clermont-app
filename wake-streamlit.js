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

  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.waitForTimeout(1500);

  const bodyText = (await page.textContent("body").catch(() => "")) || "";
  const isSleep = /zzzz|get this app back up|back up/i.test(bodyText);

  if (isSleep) {
    const wakeCandidates = [
      page.getByRole("button", { name: /yes,?\s*get this app back up/i }),
      page.getByRole("button", { name: /get this app back up/i }),
      page.getByRole("button", { name: /wake up/i }),
      page.locator("button:has-text('get this app back up')"),
      page.locator("button:has-text('Yes, get this app back up')"),
      page.locator("button:has-text('Wake up')"),
    ];

    for (const btn of wakeCandidates) {
      if ((await btn.count()) > 0) {
        await btn.first().click({ timeout: 15000 });
        break;
      }
    }

    await page.waitForTimeout(2500);
    await page.reload({ waitUntil: "domcontentloaded", timeout: 120000 });
  }

  await page.waitForSelector('[data-testid="stAppViewContainer"]', { timeout: 120000 });
  await page.waitForSelector("text=Décrivez votre bien", { timeout: 120000 });

  console.log("OK ✅");

  await browser.close();
})();
