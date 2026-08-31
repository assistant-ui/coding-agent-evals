import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  type UIMessage,
} from "ai";

export const maxDuration = 30;

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
  const body = (await req.json()) as {
    messages: UIMessage[];
    config?: { modelName?: string; reasoningEffort?: string };
  };
  const { messages, config } = body;
  const modelName = config?.modelName ?? "gpt-stub-a";
  const userText = lastUserText(messages);

  const stream = createUIMessageStream({
    originalMessages: messages,
    execute: async ({ writer }) => {
      const messageId = `msg-${crypto.randomUUID()}`;
      writer.write({ type: "start", messageId });
      writer.write({ type: "start-step" });

      const textId = "reply";
      const reply = `Using model: ${modelName}. You said: ${userText || "(empty)"}`;
      writer.write({ type: "text-start", id: textId });
      writer.write({ type: "text-delta", id: textId, delta: reply });
      writer.write({ type: "text-end", id: textId });
      writer.write({ type: "finish-step" });
      writer.write({ type: "finish" });
    },
  });

  return createUIMessageStreamResponse({ stream });
}
