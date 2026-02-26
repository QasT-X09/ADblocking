"ui";

/**
 * Auto.js script: taps buttons containing skip/close keywords.
 *
 * Runs fully on Android phone (no PC/ADB required).
 * Requirements:
 *   - Auto.js app installed
 *   - Accessibility service enabled for Auto.js
 */

const DEFAULT_KEYWORDS = [
  "skip",
  "skip ad",
  "skip ads",
  "пропустить",
  "закрыть",
  "close",
];

const CHECK_INTERVAL_MS = 800;
const TOAST_INTERVAL_MS = 5000;

let lastToastAt = 0;
let taps = 0;

function now() {
  return new Date().getTime();
}

function notifyThrottled(message) {
  const t = now();
  if (t - lastToastAt >= TOAST_INTERVAL_MS) {
    toast(message);
    lastToastAt = t;
  }
}

function hasKeyword(text, keywords) {
  if (!text) return false;
  const low = String(text).toLowerCase();
  for (let i = 0; i < keywords.length; i += 1) {
    if (low.indexOf(keywords[i]) !== -1) return true;
  }
  return false;
}

function clickNode(node) {
  if (!node) return false;
  if (node.click()) return true;

  const b = node.bounds();
  if (!b) return false;
  return click(b.centerX(), b.centerY());
}

function findAndTap(keywords) {
  const clickable = classNameMatches(/.*/).clickable(true).find();
  for (let i = 0; i < clickable.size(); i += 1) {
    const node = clickable.get(i);
    const txt = node.text();
    const desc = node.desc();
    const id = node.id();

    const matched =
      hasKeyword(txt, keywords) ||
      hasKeyword(desc, keywords) ||
      hasKeyword(id, keywords);

    if (!matched) continue;

    const tapped = clickNode(node);
    if (tapped) {
      taps += 1;
      log("Tapped candidate #" + taps + ": text=" + txt + ", desc=" + desc + ", id=" + id);
      return true;
    }
  }
  return false;
}

function normalizeKeywords(list) {
  return list.map((x) => String(x).toLowerCase().trim()).filter((x) => x.length > 0);
}

function main() {
  auto.waitFor();

  const keywords = normalizeKeywords(DEFAULT_KEYWORDS);
  toast("Skip helper started");
  log("Keywords: " + JSON.stringify(keywords));
  log("Press volume up in Auto.js to stop script");

  while (true) {
    try {
      const pressed = findAndTap(keywords);
      if (!pressed) {
        notifyThrottled("Skip helper: no matching button");
      }
    } catch (e) {
      log("Warning: " + e);
      notifyThrottled("Skip helper warning: " + e);
    }
    sleep(CHECK_INTERVAL_MS);
  }
}

main();
