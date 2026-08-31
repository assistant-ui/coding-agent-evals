import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  type UIMessage,
} from "ai";

export const maxDuration = 30;

const SAMPLE_URI = "ui://sample/widget.html";
const SAMPLE_TOOL = "show_sample_app";
const ECHO_TOOL = "local-test__echo";

function lastUserText(messages: UIMessage[]): string {
  const last = [...messages].reverse().find((message) => message.role === "user");
  if (!last) {
    return "";
  }
  return last.parts
    .flatMap((part) => (part.type === "text" ? [part.text] : []))
    .join(" ");
}

function wantsWidget(text: string): boolean {
  return /show|sample|mcp app|widget/i.test(text);
}

function echoToolName(tools: Record<string, unknown> | undefined): string {
  const names = Object.keys(tools ?? {});
  return (
    names.find((name) => name.endsWith("__echo") || name === "echo") ?? ECHO_TOOL
  );
}

export async function POST(req: Request) {
  const { messages, tools }: { messages: UIMessage[]; tools?: Record<string, unknown> } =
    await req.json();
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
          delta: "Ready.",
        });
        writer.write({ type: "text-end", id: textId });
        writer.write({ type: "finish-step" });
        writer.write({ type: "finish" });
        return;
      }

      if (wantsWidget(userText)) {
        const toolCallId = `call-${crypto.randomUUID()}`;
        writer.write({
          type: "tool-input-available",
          toolCallId,
          toolName: SAMPLE_TOOL,
          input: { prompt: userText },
          providerMetadata: {
            mcp: {
              app: {
                resourceUri: SAMPLE_URI,
                mimeType: "text/html;profile=mcp-app",
              },
            },
          },
        });
        writer.write({
          type: "tool-output-available",
          toolCallId,
          output: {
            content: [{ type: "text", text: "Sample MCP app ready" }],
            _meta: {
              ui: { resourceUri: SAMPLE_URI },
            },
          },
        });
        const textId = "ack";
        writer.write({ type: "text-start", id: textId });
        writer.write({
          type: "text-delta",
          id: textId,
          delta: "Opened the sample MCP app.",
        });
        writer.write({ type: "text-end", id: textId });
        writer.write({ type: "finish-step" });
        writer.write({ type: "finish" });
        return;
      }

      writer.write({
        type: "tool-input-available",
        toolCallId: `call-${crypto.randomUUID()}`,
        toolName: echoToolName(tools),
        input: { text: userText || "ping" },
      });
      writer.write({ type: "finish-step" });
      writer.write({ type: "finish" });
    },
  });

  return createUIMessageStreamResponse({ stream });
}
