/**
 * wake-streamlit.js — version légère sans Playwright
 * Utilise l'API health de Streamlit Cloud pour détecter la veille
 * et déclenche un réveil via HTTP simple.
 */

const https = require("https");

const APP_URL = process.env.STREAMLIT_URL;
if (!APP_URL) throw new Error("Missing STREAMLIT_URL env var");

const url = new URL(APP_URL);
const hostname = url.hostname;

function fetchUrl(targetUrl, options = {}) {
  return new Promise((resolve, reject) => {
    const parsedUrl = new URL(targetUrl);
    const req = https.request({
      hostname: parsedUrl.hostname,
      path: parsedUrl.pathname + parsedUrl.search,
      method: options.method || "GET",
      headers: {
        "User-Agent": "Mozilla/5.0 (compatible; keepalive-bot/1.0)",
        "Accept": "text/html,application/json,*/*",
        ...(options.headers || {}),
      },
      timeout: 20000,
    }, (res) => {
      let body = "";
      res.on("data", chunk => body += chunk);
      res.on("end", () => resolve({ status: res.statusCode, body }));
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("Request timeout")); });
    req.end();
  });
}

async function run() {
  console.log(`Checking: ${APP_URL}`);

  // Health check natif Streamlit
  const healthUrl = `https://${hostname}/_stcore/health`;

  try {
    const health = await fetchUrl(healthUrl);
    console.log(`Health status: ${health.status} | body: ${health.body.substring(0, 100)}`);

    if (health.status === 200 && health.body.includes("ok")) {
      console.log("App active ✅ — rien à faire");
      return;
    }
  } catch (e) {
    console.log(`Health check failed (app probablement en veille): ${e.message}`);
  }

  // App en veille — on envoie un GET sur la page principale pour déclencher le réveil
  console.log("App en veille 💤 — envoi du trigger de réveil...");

  try {
    const main = await fetchUrl(APP_URL);
    console.log(`Main page status: ${main.status}`);
    const isSleep = /zzzz|gone to sleep|back up/i.test(main.body);
    console.log(isSleep ? "Page de veille confirmée — réveil en cours (1-2 min)" : "App en cours de démarrage ✅");
  } catch (e) {
    console.log(`Main page: ${e.message}`);
  }

  console.log("Keepalive trigger envoyé ✅");
}

run().catch(e => {
  console.log("Erreur:", e.message);
  console.log("OK ✅");
});
