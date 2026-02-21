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

  async function getBodySnippet() {
    const body = (await page.textContent("body").catch(() => "")) || "";
    return body.replace(/\s+/g, " ").slice(0, 700);
  }

  async function debug(label) {
    const title = await page.title().catch(() => "");
    const snippet = await getBodySnippet();
    console.log(`\n=== DEBUG (${label}) ===`);
    console.log("TITLE:", title);
    console.log("BODY_SNIPPET:", snippet);
    console.log("=== END DEBUG ===\n");
  }

  // 1) Load page
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.waitForTimeout(1500);

  // 2) Detect sleep screen
  const bodyText = (await page.textContent("body").catch(() => "")) || "";
  const isSleep = /zzzz|get this app back up|back up/i.test(bodyText);

  if (isSleep) {
    console.log("Sleep screen detected 💤");
    await debug("sleep-detected");

    const wakeCandidates = [
      page.getByRole("button", { name: /yes,?\s*get this app back up/i }),
      page.getByRole("button", { name: /get this app back up/i }),
      page.locator("button:has-text('Yes, get this app back up')"),
      page.locator("button:has-text('get this app back up')"),
      page.getByRole("button", { name: /wake up/i }),
      page.locator("button:has-text('Wake up')"),
    ];

    let clicked = false;
    for (const btn of wakeCandidates) {
      if ((await btn.count()) > 0) {
        await btn.first().click({ timeout: 15000 });
        clicked = true;
        console.log("Wake button clicked ✅");
        break;
      }
    }

    if (!clicked) {
      console.log("Sleep detected but no wake button found ⚠️");
      await debug("sleep-no-button");
    }

    // Reload after click: often required by Streamlit
    await page.waitForTimeout(2500);
    await page.reload({ waitUntil: "domcontentloaded", timeout: 120000 });
    await page.waitForTimeout(1500);
  } else {
    console.log("No sleep screen detected ✅");
  }

  // 3) Proof of life (robust)
  // We prefer checking for YOUR app’s texts rather than Streamlit testids,
  // because Streamlit DOM can vary.
  let uiConfirmed = false;
  try {
    await Promise.race([
      page.waitForSelector("text=Décrivez votre bien", { timeout: 60000 }),
      page.waitForSelector("text=Obtenir mon estimation gratuite", { timeout: 60000 }),
      page.waitForSelector("text=Pourquoi choisir mon estimation", { timeout: 60000 }),
      // fallback Streamlit selectors (if present)
      page.waitForSelector('[data-testid="stApp"]', { timeout: 60000 }),
      page.waitForSelector('[data-testid="stHeader"]', { timeout: 60000 }),
    ]);
    uiConfirmed = true;
  } catch (e) {
    uiConfirmed = false;
  }

  if (uiConfirmed) {
    console.log("Awake + UI proof detected ✅");
  } else {
    console.log("Wake attempted ✅ (UI proof not confirmed yet)");
    await debug("no-ui-proof");
    // IMPORTANT: We do NOT fail the workflow here, because the main objective is to wake the app.
  }

  await browser.close();
})();
