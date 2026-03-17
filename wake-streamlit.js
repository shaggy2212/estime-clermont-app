const { chromium } = require("playwright");

(async () => {
  const url = process.env.STREAMLIT_URL;
  if (!url) throw new Error("Missing STREAMLIT_URL env var");

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 720 },
  });

  const HARD_TIMEOUT_MS = 90000;
  const hardTimeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error("Hard timeout reached")), HARD_TIMEOUT_MS)
  );

  async function run() {
    await page.goto(url, { waitUntil: "networkidle", timeout: 40000 });

    // Attendre que Streamlit ait vraiment rendu quelque chose
    // Soit l'app active, soit la page de veille
    try {
      await Promise.race([
        page.waitForSelector('[data-testid="stApp"]', { timeout: 15000 }),
        page.waitForSelector("text=This app has gone to sleep", { timeout: 15000 }),
        page.waitForSelector("text=Zzzz", { timeout: 15000 }),
        page.waitForSelector("button", { timeout: 15000 }),
      ]);
    } catch (e) {
      console.log("Rien de reconnaissable rendu après 15s, on continue quand même...");
    }

    // Pause supplémentaire pour le rendu complet
    await page.waitForTimeout(3000);

    const bodyText = (await page.textContent("body").catch(() => "")) || "";
    console.log("Body snippet:", bodyText.substring(0, 400));

    const isSleep =
      /zzzz|get this app back up|back up|this app has gone to sleep|wake it up|yes, get this app|app has gone to sleep/i.test(bodyText);

    if (isSleep) {
      console.log("Sleep detected 💤 — tentative de réveil...");

      const selectors = [
        "button:has-text('Yes, get this app back up!')",
        "button:has-text('get this app back up')",
        "button:has-text('Wake up')",
        "button:has-text('wake it up')",
        "[data-testid='stWakeupButton']",
      ];

      let clicked = false;
      for (const sel of selectors) {
        const btn = page.locator(sel).first();
        if ((await btn.count()) > 0) {
          try {
            await btn.click({ timeout: 8000 });
            console.log(`Wake clicked via: ${sel} ✅`);
            clicked = true;
            break;
          } catch (e) {
            console.log(`Selector ${sel} trouvé mais clic échoué:`, e.message);
          }
        }
      }

      if (!clicked) {
        console.log("Bouton non trouvé ⚠️ — body complet:", bodyText.substring(0, 800));
      }

      await page.waitForTimeout(5000);
      await page.reload({ waitUntil: "networkidle", timeout: 40000 });

      try {
        await page.waitForSelector('[data-testid="stApp"]', { timeout: 30000 });
        console.log("App revenue en ligne ✅");
      } catch (e) {
        console.log("App pas encore prête (peut prendre 1-2 min)");
      }

    } else {
      console.log("App déjà active ✅");
    }
  }

  try {
    await Promise.race([run(), hardTimeout]);
    console.log("Keepalive OK ✅");
  } catch (e) {
    console.log("Erreur non bloquante:", e.message);
    console.log("Keepalive OK ✅");
  } finally {
    await browser.close();
  }
})();
