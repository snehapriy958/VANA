import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const USER_DATA_DIR = path.join(process.env.TEMP || "C:\\temp", "chrome_vana_audit");
const OUT_DIR = path.resolve("docs/screenshots");

async function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  console.log("1. Preparing output directory...");
  if (!fs.existsSync(OUT_DIR)) {
    fs.mkdirSync(OUT_DIR, { recursive: true });
  }

  console.log("2. Launching headless Chrome...");
  const chrome = spawn(
    CHROME_PATH,
    [
      "--headless",
      "--remote-debugging-port=9222",
      `--user-data-dir=${USER_DATA_DIR}`,
      "--window-size=1440,900",
      "--disable-gpu",
      "--no-sandbox",
    ],
    { stdio: "ignore" }
  );

  await wait(1500);

  const vResp = await fetch("http://127.0.0.1:9222/json/version");
  const vData = await vResp.json();
  const browserWs = new WebSocket(vData.webSocketDebuggerUrl);

  const targetId = await new Promise((resolve) => {
    browserWs.onopen = () => {
      browserWs.send(
        JSON.stringify({
          id: 1,
          method: "Target.createTarget",
          params: { url: "http://127.0.0.1:5173" },
        })
      );
    };
    browserWs.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      if (msg.id === 1 && msg.result?.targetId) resolve(msg.result.targetId);
    };
  });

  console.log("3. Connected to page target:", targetId);
  const pageWs = new WebSocket(`ws://127.0.0.1:9222/devtools/page/${targetId}`);
  await new Promise((r) => (pageWs.onopen = r));

  let nextId = 100;
  const pageSend = (method, params = {}) => {
    return new Promise((resolve) => {
      const msgId = nextId++;
      const handler = (evt) => {
        const msg = JSON.parse(evt.data);
        if (msg.id === msgId) {
          pageWs.removeEventListener("message", handler);
          resolve(msg.result);
        }
      };
      pageWs.addEventListener("message", handler);
      pageWs.send(JSON.stringify({ id: msgId, method, params }));
    });
  };

  await pageSend("Page.enable");
  await pageSend("Runtime.enable");
  await pageSend("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false,
  });

  await wait(2000);

  console.log("4. Authenticating in page context...");
  const adminPassword =
    process.env.DEV_ADMIN_PASSWORD || process.env.ADMIN_PASSWORD || "SecurePass123!";

  const loginEval = await pageSend("Runtime.evaluate", {
    expression: `
      (async () => {
        try {
          const resp = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: 'admin@vana.earth', password: ${JSON.stringify(adminPassword)} })
          });
          const data = await resp.json();
          if (data.access_token) {
            sessionStorage.setItem('vana_session_access_token', data.access_token);
            sessionStorage.setItem('vana_session_refresh_token', data.refresh_token);
            return { success: true, email: 'admin@vana.earth', role: data.user?.role };
          }
          return { error: data };
        } catch (e) {
          return { error: e.message };
        }
      })()
    `,
    awaitPromise: true,
    returnByValue: true,
  });

  console.log("   Login result:", loginEval.result?.value);

  console.log("5. Navigating to /audit...");
  await pageSend("Page.navigate", { url: "http://127.0.0.1:5173/audit" });
  await wait(3500);

  const capture = async (filename) => {
    const res = await pageSend("Page.captureScreenshot", { format: "png" });
    const buffer = Buffer.from(res.data, "base64");
    const outPath = path.join(OUT_DIR, filename);
    fs.writeFileSync(outPath, buffer);
    console.log(`   Saved screenshot: ${filename} (${buffer.length} bytes)`);
  };

  console.log("6. Capturing Audit Workspaces:");

  // 1. Audit Overview
  console.log("   - Capturing Audit Overview...");
  await capture("audit_overview.png");

  // 2. Audit Timeline Tab
  console.log("   - Switching to Audit Timeline Tab...");
  await pageSend("Runtime.evaluate", {
    expression: `
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b => b.textContent && b.textContent.includes('Audit Timeline'));
        if (btn) btn.click();
      })()
    `,
  });
  await wait(2500);
  await capture("audit_timeline.png");

  // 3. Verification History Tab
  console.log("   - Switching to Verification History Tab...");
  await pageSend("Runtime.evaluate", {
    expression: `
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b => b.textContent && b.textContent.includes('Verification History'));
        if (btn) btn.click();
      })()
    `,
  });
  await wait(2500);
  await capture("audit_verification.png");

  // 4. Integrity Console Tab
  console.log("   - Switching to Integrity Console Tab...");
  await pageSend("Runtime.evaluate", {
    expression: `
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b => b.textContent && b.textContent.includes('Integrity Console'));
        if (btn) btn.click();
      })()
    `,
  });
  await wait(2000);

  console.log("   - Triggering Run Integrity Verification button...");
  await pageSend("Runtime.evaluate", {
    expression: `
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b => b.textContent && b.textContent.includes('Run Integrity Verification'));
        if (btn) btn.click();
      })()
    `,
  });
  await wait(3500); // Wait for API response and render
  await capture("audit_integrity.png");

  // 5. Entity Change History Tab
  console.log("   - Switching to Entity History Tab...");
  await pageSend("Runtime.evaluate", {
    expression: `
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b => b.textContent && b.textContent.includes('Entity History'));
        if (btn) btn.click();
      })()
    `,
  });
  await wait(2000);

  console.log("   - Clicking first project button in Entity History quick select...");
  await pageSend("Runtime.evaluate", {
    expression: `
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const pBtn = buttons.find(b => b.textContent && (b.textContent.includes('PRJ') || b.textContent.includes('DEMO') || b.textContent.includes('M8')));
        if (pBtn) pBtn.click();
      })()
    `,
  });
  await wait(2500);
  await capture("audit_entity_history.png");

  console.log("7. Closing browser...");
  pageWs.close();
  browserWs.close();
  chrome.kill();
  console.log("ALL 5 AUDIT WORKSPACE SCREENSHOTS CAPTURED SUCCESSFULLY!");
}

main().catch((err) => {
  console.error("Browser acceptance error:", err);
  process.exit(1);
});
