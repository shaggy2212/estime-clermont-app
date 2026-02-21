const { chromium } = require("playwright");

(async () => {
  const url = process.env.STREAMLIT_URL;
  if (!url) throw new Error("Missing STREAMLIT_URL env var");

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });

  // Cherche un bouton de réveil avec plusieurs variantes
  const wakeCandidates = [
    page.getByRole("button", { name: /get this app back up/i }),
    page.getByRole("button", { name: /wake up/i }),
    page.getByRole("button", { name: /relancer|réveiller|remettre/i }),
    page.locator("button:has-text('get this app back up')"),
    page.locator("button:has-text('Wake up')"),
  ];

  let clicked = false;
  for (const btn of wakeCandidates) {
    if (await btn.count()) {
      await btn.first().click({ timeout: 8000 });
      clicked = true;
      break;
    }
  }

  // Attendre que Streamlit charge vraiment l'app
  await page.waitForSelector('[data-testid="stAppViewContainer"]', { timeout: 120000 });

  // Vérifie qu'un texte clé de TON app est présent
  // (ça prouve qu'on n'est plus sur la page Zzzz)
  await page.waitForSelector("text=Décrivez votre bien", { timeout: 60000 });

  console.log(clicked ? "Woke up ✅ and app loaded ✅" : "App already awake ✅");

  await browser.close();
})();
