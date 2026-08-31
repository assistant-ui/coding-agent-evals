#!/usr/bin/env node
/**
 * Patch scaffolded thread.aui.tsx:
 * - ChatGPT empty-state heading
 * - Ask anything placeholder
 * - ModelSelector in ComposerAction (registers config.modelName)
 */
import fs from "node:fs";

const target = process.argv[2];
if (!target) {
  console.error("usage: patch-thread.mjs <thread.aui.tsx>");
  process.exit(1);
}

let src = fs.readFileSync(target, "utf8");

if (!src.includes("model-selector.aui")) {
  const importLine =
    'import { ModelSelector } from "@/components/assistant-ui/elements/model-selector.aui";\n';
  if (src.includes("tooltip-icon-button")) {
    src = src.replace(
      /(import \{ TooltipIconButton \} from "[^"]+";\n)/,
      `$1${importLine}`,
    );
  } else {
    src = src.replace(/("use client";\n)/, `$1\n${importLine}`);
  }
}

if (!src.includes("GOLD_MODELS")) {
  const modelsBlock = `
const GOLD_MODELS = [
  { id: "gpt-stub-a", name: "GPT Stub A", description: "Fast stub model" },
  { id: "gpt-stub-b", name: "GPT Stub B", description: "Capable stub model" },
];
`;
  src = src.replace(
    /export function Thread\(\)/,
    `${modelsBlock}\nexport function Thread()`,
  );
}

src = src.replace(
  /How can I help you today\?/,
  "Where should we begin?",
);

src = src.replace(
  /placeholder="Send a message\.\.\."/,
  'placeholder="Ask anything"',
);

if (!src.includes("<ModelSelector")) {
  // Insert ModelSelector immediately after ComposerAddAttachment in ComposerAction.
  const needle = "<ComposerAddAttachment />";
  const idx = src.lastIndexOf(needle);
  if (idx < 0) {
    console.error("ComposerAddAttachment not found; patch aborted");
    process.exit(1);
  }
  const insert = `${needle}

      <div className="ml-auto flex items-center gap-1" data-testid="g10-model-selector">
      <ModelSelector
        models={GOLD_MODELS}
        defaultValue="gpt-stub-a"
        variant="ghost"
        size="sm"
        align="end"
        className="h-7 rounded-full"
      />
      </div>`;
  src = src.slice(0, idx) + insert + src.slice(idx + needle.length);

  // Flex layout so selector sits with send/cancel on the right.
  src = src.replace(
    /function ComposerAction\(\) \{\s*return \(\s*<div className="relative flex items-center justify-between">/,
    'function ComposerAction() {\n  return (\n    <div className="relative flex items-center justify-between gap-2">',
  );
}

fs.writeFileSync(target, src);
console.log("patched", target);
