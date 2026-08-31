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
          delta: "Updated the form fields.",
        });
        writer.write({ type: "text-end", id: textId });
        writer.write({ type: "finish-step" });
        writer.write({ type: "finish" });
        return;
      }

      if (/submit/i.test(userText)) {
        writer.write({
          type: "tool-input-available",
          toolCallId: `call-${crypto.randomUUID()}`,
          toolName: "submit_form",
          input: {},
        });
        const textId = "ack";
        writer.write({ type: "text-start", id: textId });
        writer.write({
          type: "text-delta",
          id: textId,
          delta: "Submitted the form.",
        });
        writer.write({ type: "text-end", id: textId });
      } else {
        writer.write({
          type: "tool-input-available",
          toolCallId: `call-${crypto.randomUUID()}`,
          toolName: "set_form_field",
          input: { name: "firstName", value: "Alex" },
        });
        writer.write({
          type: "tool-input-available",
          toolCallId: `call-${crypto.randomUUID()}`,
          toolName: "set_form_field",
          input: { name: "lastName", value: "Rivera" },
        });
        writer.write({
          type: "tool-input-available",
          toolCallId: `call-${crypto.randomUUID()}`,
          toolName: "set_form_field",
          input: { name: "email", value: "alex@example.com" },
        });
        const textId = "ack";
        writer.write({ type: "text-start", id: textId });
        writer.write({
          type: "text-delta",
          id: textId,
          delta: "Filled name and email on the form.",
        });
        writer.write({ type: "text-end", id: textId });
      }

      writer.write({ type: "finish-step" });
      writer.write({ type: "finish" });
    },
  });

  return createUIMessageStreamResponse({ stream });
}
