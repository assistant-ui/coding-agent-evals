import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  type UIMessage,
} from "ai";

export const maxDuration = 30;

const CARD_HTML = `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Sample card</title>
    <style>
      body { font-family: system-ui, sans-serif; padding: 24px; }
      .card { border: 1px solid #d1d5db; border-radius: 12px; padding: 20px; max-width: 320px; }
      h1 { margin: 0 0 12px; font-size: 1.25rem; }
      p { color: #374151; margin: 0 0 16px; }
      button { background: #2563eb; color: white; border: 0; padding: 8px 16px; border-radius: 8px; }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Welcome</h1>
      <p>A short note about this sample card.</p>
      <button type="button">Continue</button>
    </div>
  </body>
</html>`;

const LAUNCH_HTML = `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Sample card</title>
    <style>
      body { font-family: system-ui, sans-serif; padding: 24px; }
      .card { border: 1px solid #d1d5db; border-radius: 12px; padding: 20px; max-width: 320px; }
      h1 { margin: 0 0 12px; font-size: 1.25rem; }
      p { color: #374151; margin: 0 0 16px; }
      button { background: #2563eb; color: white; border: 0; padding: 8px 16px; border-radius: 8px; }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Welcome</h1>
      <p>A shorter note.</p>
      <button type="button">Launch</button>
    </div>
  </body>
</html>`;

function lastUserText(messages: UIMessage[]): string {
  const last = [...messages].reverse().find((message) => message.role === "user");
  if (!last) {
    return "";
  }
  return last.parts
    .flatMap((part) => (part.type === "text" ? [part.text] : []))
    .join(" ");
}

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();
  const last = messages.at(-1);
  const userText = lastUserText(messages);

  const stream = createUIMessageStream({
    originalMessages: messages,
    execute: async ({ writer }) => {
      const messageId = `msg-${crypto.randomUUID()}`;
      writer.write({ type: "start", messageId });
      writer.write({ type: "start-step" });

      if (last?.role !== "user") {
        const textId = "ack";
        writer.write({ type: "text-start", id: textId });
        writer.write({
          type: "text-delta",
          id: textId,
          delta: "Rendered the HTML on the canvas.",
        });
        writer.write({ type: "text-end", id: textId });
        writer.write({ type: "finish-step" });
        writer.write({ type: "finish" });
        return;
      }

      const launch = /launch/i.test(userText);
      const toolCallId = `call-${crypto.randomUUID()}`;
      writer.write({
        type: "tool-input-available",
        toolCallId,
        toolName: "artifact",
        input: {
          title: launch ? "Launch card" : "Sample card",
          code: launch ? LAUNCH_HTML : CARD_HTML,
        },
      });
      writer.write({
        type: "tool-output-available",
        toolCallId,
        output: { success: true },
      });
      const textId = "ack";
      writer.write({ type: "text-start", id: textId });
      writer.write({
        type: "text-delta",
        id: textId,
        delta: "Rendered the HTML on the canvas.",
      });
      writer.write({ type: "text-end", id: textId });
      writer.write({ type: "finish-step" });
      writer.write({ type: "finish" });
    },
  });

  return createUIMessageStreamResponse({ stream });
}
