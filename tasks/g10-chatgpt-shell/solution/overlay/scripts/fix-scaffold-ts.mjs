#!/usr/bin/env node
/**
 * Scaffold TS fixes for current assistant-ui create (React 19 / Base UI).
 * Safe to re-run.
 */
import fs from "node:fs";
import path from "node:path";

const root = process.argv[2] || process.cwd();

const thread = path.join(
  root,
  "components/assistant-ui/elements/thread.aui.tsx",
);
const tip = path.join(
  root,
  "components/assistant-ui/elements/tooltip-icon-button.tsx",
);

let s = fs.readFileSync(thread, "utf8");

// Normalize a previous bad cast: `}} as CSSProperties` outside the JSX expr.
s = s.replace(
  /\}\} as (?:React\.)?CSSProperties(\s*\n\s*>)/,
  "} as CSSProperties}$1",
);

if (!s.includes("} as CSSProperties}") && !s.includes("} as React.CSSProperties}")) {
  if (!s.includes("--thread-max-width")) {
    console.error("thread style block missing");
    process.exit(1);
  }

  const hasReactStar = /import \* as React from/.test(s);
  if (!hasReactStar && !/from ["']react["']/.test(s)) {
    s = s.replace(
      '"use client";\n',
      '"use client";\n\nimport type { CSSProperties } from "react";\n',
    );
  } else if (
    !hasReactStar &&
    /import \{[^}]*\} from ["']react["']/.test(s) &&
    !s.includes("CSSProperties")
  ) {
    s = s.replace(
      /import \{([^}]*)\} from (["'])react\2/,
      "import {$1, type CSSProperties } from $2react$2",
    );
  } else if (!hasReactStar && !s.includes("CSSProperties")) {
    s = s.replace(
      '"use client";\n',
      '"use client";\n\nimport type { CSSProperties } from "react";\n',
    );
  }

  const cast = hasReactStar ? "as React.CSSProperties" : "as CSSProperties";
  // style={{ ... }}  ->  style={{ ... } as CSSProperties}
  s = s.replace(
    /(style=\{\{[\s\S]*?--thread-max-width[\s\S]*?)(\}\})(\s*\n\s*>)/,
    `$1} ${cast}}$3`,
  );
}

fs.writeFileSync(thread, s);
console.log("patched", thread);

let t = fs.readFileSync(tip, "utf8");
const t2 = t.replace(/\s*delayDuration=\{\d+\}/g, "");
if (t2 !== t) {
  fs.writeFileSync(tip, t2);
  console.log("patched", tip);
} else {
  console.log("tooltip unchanged");
}
