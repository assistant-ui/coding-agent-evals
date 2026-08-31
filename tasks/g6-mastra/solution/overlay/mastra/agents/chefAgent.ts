import { Agent } from "@mastra/core/agent";

export const chefAgent = new Agent({
  id: "chef-agent",
  name: "chef-agent",
  instructions:
    "You are Michel, a practical and experienced home chef. " +
    "You help people cook with whatever ingredients they have available.",
  model: "openai/gpt-5.6-luna",
});
