const { chromium } = require("playwright");

(async () => {
  const url = process.env.STREAMLIT_URL;
  if (!url) throw new Error("Missing STREAMLIT_URL env var");

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Charge la page
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });

  // Si l'app dort, Streamlit affiche le bouton "Yes, get this app back up!"
  // On tente plusieurs sélecteurs (robustes aux variations).
  const wakeSelectors = [
    'button:has-text("Yes, get this app back up")',
    'button:has-text("get this app back up")',
    'button:has-text("Wake up")',
  ];

  let clicked = false;
  for (const sel of wakeSelectors) {
    const btn = page.locator(sel);
    if (await btn.count()) {
      await btn.first().click({ timeout: 5000 });
      clicked = true;
      break;
    }
  }

  // Attendre que l'app soit réellement chargée (ou au moins qu'on sorte de l'écran "Zzzz")
  // On attend soit la disparition du bouton, soit un élément Streamlit classique.
  try {
    await Promise.race([
      page.waitForSelector('button:has-text("Yes, get this app back up")', { state: "detached", timeout: 90000 }),
      page.waitForSelector('[data-testid="stAppViewContainer"]', { timeout: 90000 }),
    ]);
  } catch (e) {
    // On ne fail pas forcément: l'objectif est de "taper" l'app.
  }

  console.log(clicked ? "Wake button clicked ✅" : "No wake button found (app likely already awake) ✅");

  await browser.close();
})();
