import { createServerFn } from "@tanstack/react-start";

type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};

type ChatInput = {
  messages: ChatMessage[];
};

export const chatStream = createServerFn({ method: "POST" })
  .inputValidator((data: ChatInput) => data)
  .handler(async function* ({ data }) {
    const last = data.messages.at(-1)?.content ?? "";
    yield `You said: ${last}`;
  });
