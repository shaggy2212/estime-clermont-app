const { chromium } = require("playwright");

(async () => {
  const url = process.env.STREAMLIT_URL;
  if (!url) throw new Error("Missing STREAMLIT_URL env var");

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 720 },
  });

  // Hard timeout global (évite les runs à rallonge)
  const HARD_TIMEOUT_MS = 30000;
  const hardTimeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error("Hard timeout reached")), HARD_TIMEOUT_MS)
  );

  async function run() {
    // Charge vite (on ne cherche pas la stabilité parfaite)
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 20000 });
    await page.waitForTimeout(600);

    const bodyText = (await page.textContent("body").catch(() => "")) || "";
    const isSleep = /zzzz|get this app back up|back up/i.test(bodyText);

    if (isSleep) {
      console.log("Sleep detected 💤");

      const wakeBtn =
        page.getByRole("button", { name: /get this app back up/i }).first();

      if (await wakeBtn.count()) {
        await wakeBtn.click({ timeout: 8000 });
        console.log("Wake clicked ✅");
      } else {
        // fallback si le role ne matche pas
        const alt = page.locator("button:has-text('get this app back up')").first();
        if (await alt.count()) {
          await alt.click({ timeout: 8000 });
          console.log("Wake clicked (fallback) ✅");
        } else {
          console.log("Wake button not found ⚠️");
        }
      }

      // Reload après clic, puis une preuve légère (max 12s)
      await page.waitForTimeout(1200);
      await page.reload({ waitUntil: "domcontentloaded", timeout: 20000 });

      try {
        await Promise.race([
          page.waitForSelector("text=Décrivez votre bien", { timeout: 12000 }),
          page.waitForSelector("text=Obtenir mon estimation gratuite", { timeout: 12000 }),
          page.waitForSelector('[data-testid="stApp"]', { timeout: 12000 }),
        ]);
        console.log("UI proof detected ✅");
      } catch (e) {
        console.log("UI proof not confirmed (still fine) ✅");
      }
    } else {
      console.log("No sleep detected ✅ (touch done)");
      // Pas besoin d’attendre 60s : on a déjà “touché” l’app.
    }
  }

  try {
    await Promise.race([run(), hardTimeout]);
    console.log("OK ✅");
  } catch (e) {
    // On préfère ne PAS faire échouer le workflow si Streamlit est lent.
    // L’objectif principal est de maintenir l’app active.
    console.log("Non-blocking error:", e.message);
    console.log("OK ✅");
  } finally {
    await browser.close();
  }
})();
