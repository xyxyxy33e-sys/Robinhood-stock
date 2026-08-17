// Fetch SPMO (Invesco S&P 500 Momentum ETF) holdings from Invesco's website.
//
// Invesco's product page is a JS app behind an Akamai WAF that rejects plain
// HTTP clients (406), so this drives headless Chromium and captures the
// holdings XHR the page makes to dng-api.invesco.com.
//
// Environment notes (Claude Code remote container):
// - Chromium is pre-installed at /opt/pw-browsers/chromium; do NOT run
//   "playwright install". Requires: npm install playwright-core
// - Outbound HTTPS goes through the agent proxy (HTTPS_PROXY). The proxy's
//   MITM cannot complete Chromium's TLS 1.3 handshake (connection reset), so
//   --ssl-version-max=tls1.2 is required, and the re-signed certs need
//   --ignore-certificate-errors / ignoreHTTPSErrors.
//
// Usage: node fetch-spmo-holdings.js [topN]
// Prints JSON: { effectiveBusinessDate, totalNumberOfHoldings, top: [{ticker, name, weight}] }

const { chromium } = require('playwright-core');

const TOP_N = parseInt(process.argv[2] || '10', 10);

(async () => {
  const browser = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium',
    args: ['--no-sandbox', '--ssl-version-max=tls1.2', '--ignore-certificate-errors'],
    proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined,
  });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
    ignoreHTTPSErrors: true,
  });
  const page = await ctx.newPage();

  let holdingsPayload = null;
  page.on('response', async (res) => {
    if (/dng-api\.invesco\.com\/.*\/holdings\/fund/.test(res.url()) && res.status() === 200) {
      try {
        const j = await res.json();
        if (j && Array.isArray(j.holdings) && j.holdings.length) holdingsPayload = j;
      } catch (e) {}
    }
  });

  await page.goto(
    'https://www.invesco.com/us/financial-products/etfs/product-detail?audienceType=Investor&ticker=SPMO',
    { waitUntil: 'domcontentloaded', timeout: 90000 }
  );
  for (let i = 0; i < 30 && !holdingsPayload; i++) await page.waitForTimeout(1000);
  await browser.close();

  if (!holdingsPayload) {
    console.error('FAILED: no holdings XHR captured from Invesco');
    process.exit(1);
  }

  const top = holdingsPayload.holdings
    .filter((h) => h.ticker)
    .sort((a, b) => b.percentageOfTotalNetAssets - a.percentageOfTotalNetAssets)
    .slice(0, TOP_N)
    .map((h) => ({
      ticker: h.ticker,
      name: h.issuerName.replace(/&amp;/g, '&'),
      weight: h.percentageOfTotalNetAssets,
    }));

  console.log(JSON.stringify({
    effectiveBusinessDate: holdingsPayload.effectiveBusinessDate,
    totalNumberOfHoldings: holdingsPayload.totalNumberOfHoldings,
    top,
  }, null, 2));
})().catch((e) => { console.error('FAILED:', e.message); process.exit(1); });
