// "issue_reassigned" iptallerinin üç grubu (AJA-2669). Bütün veri sahtedir.
import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

const DATA = JSON.parse(readFileSync(new URL("./fixtures/data.json", import.meta.url), "utf8"));

async function open(page, data = DATA) {
  await page.route("**/api/data", (route) => route.fulfill({ json: data }));
  await page.route("**/api/burndown**", (route) => route.fulfill({ json: { error: "Sahte veride burndown yok." } }));
  await page.goto("/");
  await expect(page.locator("#iptal-gruplari .kpi").first()).toBeVisible();
}

const tile = (page, name) => page.locator("#iptal-gruplari .kpi").filter({ has: page.getByText(name, { exact: true }) });

test("üç sayı ayrı ayrı ve doğru adla görünür", async ({ page }) => {
  await open(page);
  await expect(page.getByRole("heading", { name: "Devir iptalleri" })).toBeVisible();
  await expect(page.locator("#iptal-gruplari .kpi")).toHaveCount(3);
  await expect(tile(page, "Normal devir").locator(".v")).toHaveText("120");
  await expect(tile(page, "Kesilen çalışma").locator(".v")).toHaveText("6");
  await expect(tile(page, "Boş uyanma").locator(".v")).toHaveText("21");
  await expect(page.locator("#iptal-ozet")).toContainText("1000");
});

test("yalnız Kesilen çalışma kayıp diye işaretlidir", async ({ page }) => {
  await open(page);
  const lost = page.locator('#iptal-gruplari .kpi[data-loss="true"]');
  await expect(lost).toHaveCount(1);
  await expect(lost).toContainText("Kesilen çalışma");
  // The mark is a word, not only a colour.
  await expect(lost.getByText("Kayıp", { exact: true })).toBeVisible();
  await expect(tile(page, "Normal devir").getByText("Kayıp", { exact: true })).toHaveCount(0);
  await expect(tile(page, "Boş uyanma").getByText("Kayıp", { exact: true })).toHaveCount(0);
  await expect(page.locator("#iptal-gruplari").getByText("Kayıp", { exact: true })).toHaveCount(1);
});

test("devri yapan bulunamayan çalışma sayısı yazıyla söylenir", async ({ page }) => {
  await open(page, { ...DATA, reassign: { ...DATA.reassign, unknownActor: 2 } });
  await expect(page.locator("#iptal-not")).toContainText("2 çalışmada devri yapan bulunamadı");
});

test("devri yapan hep bulunduysa not görünmez", async ({ page }) => {
  await open(page);
  await expect(page.locator("#iptal-not")).toBeHidden();
});

test("çalışma kayıtları okunamazsa bölüm bunu söyler", async ({ page }) => {
  const { reassign, ...rest } = DATA;
  await page.route("**/api/data", (route) => route.fulfill({ json: { ...rest, errors: ["Çalışma kayıtları okunamadı: sahte hata"] } }));
  await page.route("**/api/burndown**", (route) => route.fulfill({ json: { error: "Sahte veride burndown yok." } }));
  await page.goto("/");
  await expect(page.locator("#iptal-gruplari")).toContainText("Çalışma kayıtları okunamadı.");
  await expect(page.locator("#iptal-gruplari .kpi")).toHaveCount(0);
});

test("sayfa yatay taşmaz", async ({ page }) => {
  await open(page);
  const { scroll, client } = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  expect(scroll).toBeLessThanOrEqual(client);
  const box = await page.locator("#iptaller").boundingBox();
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize().width);
});

test("görünen bütün yazı en az 14 pikseldir", async ({ page }) => {
  await open(page);
  const small = await page.evaluate(() => {
    const out = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const el = n.parentElement;
      if (!n.textContent.trim() || el.closest("script, style") || !el.getClientRects().length) continue;
      const px = parseFloat(getComputedStyle(el).fontSize);
      if (px < 14) out.push(`${px}px: ${n.textContent.trim().slice(0, 40)}`);
    }
    return out;
  });
  expect(small).toEqual([]);
});

test("bölüme üst menüden gidilir", async ({ page }) => {
  await open(page);
  const link = page.getByRole("navigation", { name: "Bölümler" }).getByRole("link", { name: "İptaller" });
  await expect(link).toHaveAttribute("href", "#iptaller");
});
