import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  type UIMessage,
} from "ai";

const WEATHER_OUTPUT = {
  success: true as const,
  location: "San Francisco",
  temperature: 64,
  weatherCode: 0,
  windSpeed: 8,
  forecast: [
    { label: "Today", code: 0, min: 55, max: 68 },
    { label: "Sat", code: 2, min: 54, max: 66 },
    { label: "Sun", code: 61, min: 52, max: 63 },
    { label: "Mon", code: 0, min: 53, max: 67 },
    { label: "Tue", code: 3, min: 54, max: 65 },
  ],
};

function lastUserText(messages: UIMessage[]): string {
  const last = [...messages].reverse().find((message) => message.role === "user");
  if (!last) {
    return "";
  }
  return last.parts
    .flatMap((part) => (part.type === "text" ? [part.text] : []))
    .join(" ");
}

function hasWeatherResult(messages: UIMessage[]): boolean {
  for (const message of messages) {
    for (const part of message.parts ?? []) {
      const type = (part as { type?: string }).type ?? "";
      if (type.includes("weather_search") || type.includes("geocode_location")) {
        const state = (part as { state?: string }).state;
        if (state === "output-available" || state === "result") {
          return true;
        }
      }
    }
  }
  return false;
}

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();
  const last = messages.at(-1);
  lastUserText(messages);

  const stream = createUIMessageStream({
    originalMessages: messages,
    execute: async ({ writer }) => {
      const messageId = `msg-${crypto.randomUUID()}`;
      writer.write({ type: "start", messageId });
      writer.write({ type: "start-step" });

      if (last?.role !== "user" || hasWeatherResult(messages)) {
        const textId = "ack";
        writer.write({ type: "text-start", id: textId });
        writer.write({
          type: "text-delta",
          id: textId,
          delta: "Here is the forecast.",
        });
        writer.write({ type: "text-end", id: textId });
        writer.write({ type: "finish-step" });
        writer.write({ type: "finish" });
        return;
      }

      const toolCallId = `call-${crypto.randomUUID()}`;
      writer.write({
        type: "tool-input-available",
        toolCallId,
        toolName: "weather_search",
        input: {
          query: "San Francisco",
          longitude: -122.4194,
          latitude: 37.7749,
        },
      });
      writer.write({
        type: "tool-output-available",
        toolCallId,
        output: WEATHER_OUTPUT,
      });
      writer.write({ type: "finish-step" });
      writer.write({ type: "finish" });
    },
  });

  return createUIMessageStreamResponse({ stream });
}
