import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const USER_DATA_DIR = path.join(process.env.TEMP || "C:\\temp", "chrome_vana_workspaces");
const OUT_DIR = path.resolve("docs/screenshots");

async function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
  console.log("1. Preparing output directory...");
  if (!fs.existsSync(OUT_DIR)) {
    fs.mkdirSync(OUT_DIR, { recursive: true });
  }

  console.log("2. Launching headless Chrome...");
  const chrome = spawn(CHROME_PATH, [
    "--headless",
    "--remote-debugging-port=9222",
    `--user-data-dir=${USER_DATA_DIR}`,
    "--window-size=1440,900",
    "--disable-gpu",
    "--no-sandbox"
  ], { stdio: 'ignore' });

  await wait(1500);

  const vResp = await fetch("http://127.0.0.1:9222/json/version");
  const vData = await vResp.json();
  const browserWs = new WebSocket(vData.webSocketDebuggerUrl);

  const targetId = await new Promise((resolve) => {
    browserWs.onopen = () => {
      browserWs.send(JSON.stringify({
        id: 1,
        method: "Target.createTarget",
        params: { url: "http://localhost:5173" }
      }));
    };
    browserWs.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      if (msg.id === 1 && msg.result?.targetId) resolve(msg.result.targetId);
    };
  });

  console.log("3. Connected to page target:", targetId);
  const pageWs = new WebSocket(`ws://127.0.0.1:9222/devtools/page/${targetId}`);
  await new Promise(r => pageWs.onopen = r);

  let nextId = 100;
  const pageSend = (method, params = {}) => {
    return new Promise((resolve) => {
      const msgId = nextId++;
      const handler = (evt) => {
        const msg = JSON.parse(evt.data);
        if (msg.id === msgId) {
          pageWs.removeEventListener('message', handler);
          resolve(msg.result);
        }
      };
      pageWs.addEventListener('message', handler);
      pageWs.send(JSON.stringify({ id: msgId, method, params }));
    });
  };

  await pageSend("Page.enable");
  await pageSend("Runtime.enable");
  await pageSend("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false
  });

  await wait(2000);

  console.log("4. Authenticating in page context...");
  const adminPassword = process.env.DEV_ADMIN_PASSWORD || process.env.ADMIN_PASSWORD;
  if (!adminPassword) {
    throw new Error("Missing required environment variable: DEV_ADMIN_PASSWORD or ADMIN_PASSWORD");
  }
  const loginEval = await pageSend("Runtime.evaluate", {
    expression: `
      (async () => {
        const resp = await fetch('http://localhost:8000/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: 'admin@vana.earth', password: ${JSON.stringify(adminPassword)} })
        });
        const data = await resp.json();
        sessionStorage.setItem('vana_session_access_token', data.access_token);
        sessionStorage.setItem('vana_session_refresh_token', data.refresh_token);
        return { success: true };
      })()
    `,
    awaitPromise: true,
    returnByValue: true
  });

  console.log("5. Navigating to /monitoring...");
  await pageSend("Page.navigate", { url: "http://localhost:5173/monitoring" });
  await wait(3500);

  const capture = async (filename) => {
    const res = await pageSend("Page.captureScreenshot", { format: "png" });
    const buffer = Buffer.from(res.data, 'base64');
    const outPath = path.join(OUT_DIR, filename);
    fs.writeFileSync(outPath, buffer);
    console.log(`   Saved screenshot: ${filename} (${buffer.length} bytes)`);
  };

  console.log("6. Capturing Workspaces:");

  // 1. Overview
  console.log("   - Capturing Monitoring Overview...");
  await capture("monitoring_overview.png");

  // 2. Field Inspections Tab
  console.log("   - Switching to Field Inspections Tab...");
  await pageSend("Runtime.evaluate", {
    expression: `
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b => b.textContent && b.textContent.includes('Field Inspections'));
        if (btn) btn.click();
      })()
    `
  });
  await wait(2000);
  await capture("monitoring_inspections.png");

  // 3. Maintenance Tasks Tab
  console.log("   - Switching to Maintenance Tasks Tab...");
  await pageSend("Runtime.evaluate", {
    expression: `
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b => b.textContent && b.textContent.includes('Maintenance Tasks'));
        if (btn) btn.click();
      })()
    `
  });
  await wait(2000);
  await capture("monitoring_tasks.png");

  // 4. Survival Monitoring Tab
  console.log("   - Switching to Survival Monitoring Tab...");
  await pageSend("Runtime.evaluate", {
    expression: `
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b => b.textContent && b.textContent.includes('Survival Monitoring'));
        if (btn) btn.click();
      })()
    `
  });
  await wait(2500);
  await capture("monitoring_survival.png");

  console.log("7. Closing browser...");
  pageWs.close();
  browserWs.close();
  chrome.kill();
  console.log("ALL 4 WORKSPACE SCREENSHOTS CAPTURED SUCCESSFULLY!");
}

main().catch(err => {
  console.error("Browser acceptance error:", err);
  process.exit(1);
});
