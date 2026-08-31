import { handleChatStream } from "@mastra/ai-sdk";
import { createUIMessageStreamResponse } from "ai";
import { mastra } from "@/mastra";

export const maxDuration = 30;

export async function POST(req: Request) {
  const params = await req.json();
  const stream = await handleChatStream({
    mastra,
    agentId: "chef-agent",
    version: "v7",
    params,
  });
  return createUIMessageStreamResponse({ stream });
}
