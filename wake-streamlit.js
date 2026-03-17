const { chromium } = require("playwright");

(async () => {
  const url = process.env.STREAMLIT_URL;
  if (!url) throw new Error("Missing STREAMLIT_URL env var");

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

  try {
    console.log("Chargement de l'app...");
    await page.goto(url, { waitUntil: "networkidle", timeout: 40000 });
    await page.waitForTimeout(4000);

    const bodyText = (await page.textContent("body").catch(() => "")) || "";
    console.log("Body snippet:", bodyText.substring(0, 300));

    const isSleep = /zzzz|get this app back up|back up|gone to sleep|wake it up|yes, get this app/i.test(bodyText);

    if (isSleep) {
      console.log("Sleep detected 💤 — réveil en cours...");

      const selectors = [
        "button:has-text('Yes, get this app back up!')",
        "button:has-text('get this app back up')",
        "button:has-text('Wake')",
        "[data-testid='stWakeupButton']",
      ];

      let clicked = false;
      for (const sel of selectors) {
        const btn = page.locator(sel).first();
        if ((await btn.count()) > 0) {
          await btn.click({ timeout: 8000 });
          console.log(`Cliqué: ${sel} ✅`);
          clicked = true;
          break;
        }
      }

      if (clicked) {
        // Attendre que Streamlit confirme le réveil
        console.log("Attente confirmation réveil...");
        await page.waitForTimeout(5000);

        try {
          await page.waitForSelector('[data-testid="stApp"]', { timeout: 30000 });
          console.log("App réveillée et chargée ✅");
        } catch (e) {
          // Parfois Streamlit prend plus de temps — le clic a quand même été enregistré
          console.log("App en cours de démarrage (le clic a été enregistré) ✅");
        }
      } else {
        const buttons = await page.locator("button").allTextContents();
        console.log("Boutons trouvés:", JSON.stringify(buttons));
      }

    } else {
      console.log("App active ✅");
    }

  } catch (e) {
    console.log("Erreur:", e.message);
  } finally {
    await browser.close();
    console.log("OK ✅");
  }
})();
