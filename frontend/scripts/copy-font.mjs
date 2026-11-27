// Copies the self-hosted Outfit font into public/. No third-party font request (SIL OFL 1.1).
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const pkg = dirname(require.resolve("@fontsource-variable/outfit/package.json"));
const pub = join(dirname(fileURLToPath(import.meta.url)), "..", "public");
mkdirSync(pub, { recursive: true });
copyFileSync(join(pkg, "files", "outfit-latin-ext-wght-normal.woff2"), join(pub, "font.woff2"));
