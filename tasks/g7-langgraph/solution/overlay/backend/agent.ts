import { AIMessage, ToolMessage } from "@langchain/core/messages";
import { END, MessagesAnnotation, START, StateGraph } from "@langchain/langgraph";

const PURCHASE = {
  ticker: "TSLA",
  companyName: "Tesla, Inc.",
  quantity: 10,
  maxPurchasePrice: 250,
};

function lastToolName(state: typeof MessagesAnnotation.State): string {
  const last = state.messages.at(-1);
  if (!last || !("name" in last) || typeof last.name !== "string") {
    return "";
  }
  return last.name;
}

async function trader(state: typeof MessagesAnnotation.State) {
  const last = state.messages.at(-1);
  if (ToolMessage.isInstance(last) || lastToolName(state) === "purchase_stock") {
    return { messages: [new AIMessage("Transaction Confirmed")] };
  }
  return {
    messages: [
      new AIMessage({
        content: "",
        tool_calls: [
          {
            id: "call-purchase-tsla",
            name: "purchase_stock",
            args: PURCHASE,
            type: "tool_call",
          },
        ],
      }),
    ],
  };
}

export const graph = new StateGraph(MessagesAnnotation)
  .addNode("trader", trader)
  .addEdge(START, "trader")
  .addEdge("trader", END)
  .compile();
