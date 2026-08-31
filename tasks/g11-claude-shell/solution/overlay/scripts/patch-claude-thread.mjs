#!/usr/bin/env node
/**
 * Claude preset polish: empty-state sparkle heading (docs clone cue).
 * Safe to re-run.
 */
import fs from "node:fs";

const target = process.argv[2];
if (!target) {
  console.error("usage: patch-claude-thread.mjs <thread.aui.tsx>");
  process.exit(1);
}

let src = fs.readFileSync(target, "utf8");

if (!src.includes("Sparkle")) {
  // lucide import block — add Sparkle
  if (src.includes('from "lucide-react"')) {
    src = src.replace(
      /import \{([\s\S]*?)\} from "lucide-react";/,
      (m, inner) => {
        if (inner.includes("Sparkle")) return m;
        const trimmed = inner.trim().replace(/,$/, "");
        return `import {\n  ${trimmed},\n  Sparkle,\n} from "lucide-react";`;
      },
    );
  } else {
    src = src.replace(
      '"use client";\n',
      '"use client";\n\nimport { Sparkle } from "lucide-react";\n',
    );
  }
}

if (!src.includes("How can I help you today?")) {
  // Insert empty-state heading before messages list when isEmpty.
  const needle = `<div className="mb-14 flex flex-col gap-y-6 empty:hidden">`;
  if (!src.includes(needle)) {
    console.error("messages container not found; patch aborted");
    process.exit(1);
  }
  const welcome = `{isEmpty && (
            <h1
              data-testid="g11-claude-welcome"
              className="mb-6 flex items-center justify-center gap-3 text-3xl tracking-tight"
              style={{ fontFamily: "Georgia, serif", color: "#1a1a18" }}
            >
              <Sparkle className="size-7 fill-[var(--accent-color)] text-[var(--accent-color)]" />
              <span>How can I help you today?</span>
            </h1>
          )}

          ${needle}`;
  src = src.replace(needle, welcome);
}

fs.writeFileSync(target, src);
console.log("patched", target);
