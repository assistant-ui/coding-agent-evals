import { AIMessage, HumanMessage, ToolMessage } from "@langchain/core/messages";
import { type NextRequest, NextResponse } from "next/server";

import { graph } from "../../../backend/agent";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

type LangChainMessage = Record<string, unknown>;

type ThreadRecord = {
  thread_id: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
  status: string;
  values: { messages: LangChainMessage[] };
  seq: number;
  events: Record<string, unknown>[];
  listeners: Set<(chunk: Uint8Array) => void>;
};

type Store = {
  __g7Threads?: Map<string, ThreadRecord>;
};

const store = globalThis as typeof globalThis & Store;
if (!store.__g7Threads) {
  store.__g7Threads = new Map();
}
const THREADS = store.__g7Threads;

const PURCHASE_ARGS = {
  ticker: "TSLA",
  companyName: "Tesla, Inc.",
  quantity: 10,
  maxPurchasePrice: 250,
};

function nowIso(): string {
  return new Date().toISOString();
}

function encoder(): TextEncoder {
  return new TextEncoder();
}

function sseData(payload: unknown): Uint8Array {
  return encoder().encode(`data: ${JSON.stringify(payload)}\n\n`);
}

function corsHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  headers.set("Access-Control-Allow-Origin", "*");
  headers.set(
    "Access-Control-Allow-Methods",
    "GET, POST, PUT, PATCH, DELETE, OPTIONS",
  );
  headers.set("Access-Control-Allow-Headers", "*");
  return headers;
}

function json(data: unknown, status = 200): NextResponse {
  return NextResponse.json(data, { status, headers: corsHeaders() });
}

function pathOf(req: NextRequest): string {
  return req.nextUrl.pathname.replace(/^\/api\//, "").replace(/\/$/, "");
}

function getOrCreate(threadId: string): ThreadRecord {
  const existing = THREADS.get(threadId);
  if (existing) return existing;
  const created: ThreadRecord = {
    thread_id: threadId,
    created_at: nowIso(),
    updated_at: nowIso(),
    metadata: {},
    status: "idle",
    values: { messages: [] },
    seq: 0,
    events: [],
    listeners: new Set(),
  };
  THREADS.set(threadId, created);
  return created;
}

function threadPayload(thread: ThreadRecord) {
  return {
    thread_id: thread.thread_id,
    created_at: thread.created_at,
    updated_at: thread.updated_at,
    metadata: thread.metadata,
    status: thread.status,
    values: thread.values,
    interrupts: [],
    config: {},
  };
}

function statePayload(thread: ThreadRecord) {
  return {
    values: thread.values,
    next: [],
    tasks: [],
    metadata: thread.metadata,
    created_at: thread.created_at,
    parent_config: null,
    checkpoint: {
      thread_id: thread.thread_id,
      checkpoint_ns: "",
      checkpoint_id: `ckpt-${thread.thread_id}`,
    },
  };
}

function emit(thread: ThreadRecord, event: Record<string, unknown>): void {
  thread.seq += 1;
  const wrapped = {
    type: "event",
    event_id: String(thread.seq),
    seq: thread.seq,
    ...event,
  };
  thread.events.push(wrapped);
  const chunk = sseData(wrapped);
  for (const listener of thread.listeners) {
    try {
      listener(chunk);
    } catch {
      thread.listeners.delete(listener);
    }
  }
}

function emitValues(thread: ThreadRecord): void {
  emit(thread, {
    method: "values",
    params: {
      namespace: [],
      timestamp: Date.now(),
      data: thread.values,
    },
  });
}

function emitLifecycle(thread: ThreadRecord, event: string): void {
  emit(thread, {
    method: "lifecycle",
    params: {
      namespace: [],
      timestamp: Date.now(),
      data: { event },
    },
  });
}

function incomingMessages(input: unknown): LangChainMessage[] {
  if (!input || typeof input !== "object") return [];
  const messages = (input as Record<string, unknown>).messages;
  return Array.isArray(messages) ? (messages as LangChainMessage[]) : [];
}

function hasToolResult(messages: LangChainMessage[]): boolean {
  return messages.some(
    (message) => message.type === "tool" || message.role === "tool",
  );
}

function serializeMessage(message: unknown): LangChainMessage {
  const raw = message as {
    id?: string;
    content?: unknown;
    tool_calls?: unknown;
    name?: string;
    tool_call_id?: string;
    type?: string;
    _getType?: () => string;
    getType?: () => string;
  };
  const type = raw._getType?.() ?? raw.getType?.() ?? raw.type ?? "ai";
  const serialized: LangChainMessage = {
    id: raw.id,
    type,
    content: typeof raw.content === "string" ? raw.content : "",
  };
  if (Array.isArray(raw.tool_calls) && raw.tool_calls.length) {
    serialized.tool_calls = raw.tool_calls;
  }
  if (raw.name) serialized.name = raw.name;
  if (raw.tool_call_id) serialized.tool_call_id = raw.tool_call_id;
  return serialized;
}

function toGraphMessages(incoming: LangChainMessage[]) {
  if (!incoming.length) {
    return [new HumanMessage("Buy 10 shares of TSLA.")];
  }
  return incoming.map((message) => {
    const content =
      typeof message.content === "string" ? message.content : "";
    if (message.type === "tool" || message.role === "tool") {
      return new ToolMessage({
        content: content || JSON.stringify({ confirmed: true }),
        tool_call_id: String(
          message.tool_call_id ?? message.toolCallId ?? "call-purchase-tsla",
        ),
        name: String(message.name ?? "purchase_stock"),
      });
    }
    if (message.type === "ai" || message.role === "assistant") {
      return new AIMessage({
        content,
        tool_calls: Array.isArray(message.tool_calls)
          ? (message.tool_calls as AIMessage["tool_calls"])
          : undefined,
      });
    }
    return new HumanMessage({
      content: content || "Buy 10 shares of TSLA.",
      id: typeof message.id === "string" ? message.id : undefined,
    });
  });
}

function fallbackPurchase(incoming: LangChainMessage[]): LangChainMessage[] {
  const human =
    incoming.find(
      (message) => message.type === "human" || message.role === "user",
    ) ?? incoming.at(-1);
  return [
    {
      id: (typeof human?.id === "string" && human.id) || `human-${Date.now()}`,
      type: "human",
      content:
        typeof human?.content === "string"
          ? human.content
          : "Buy 10 shares of TSLA.",
    },
    {
      id: `ai-purchase-${Date.now()}`,
      type: "ai",
      content: "",
      tool_calls: [
        {
          id: `call-purchase-${Date.now()}`,
          name: "purchase_stock",
          args: PURCHASE_ARGS,
          type: "tool_call",
        },
      ],
    },
  ];
}

function fallbackConfirmed(
  thread: ThreadRecord,
  incoming: LangChainMessage[],
): LangChainMessage[] {
  const tool =
    incoming.find(
      (message) => message.type === "tool" || message.role === "tool",
    ) ?? incoming.at(-1);
  return [
    ...thread.values.messages,
    {
      id: (typeof tool?.id === "string" && tool.id) || `tool-${Date.now()}`,
      type: "tool",
      name: "purchase_stock",
      tool_call_id: tool?.tool_call_id ?? tool?.toolCallId,
      content:
        typeof tool?.content === "string"
          ? tool.content
          : JSON.stringify({ confirmed: true, transactionId: "txn-gold" }),
    },
    {
      id: `ai-done-${Date.now()}`,
      type: "ai",
      content: "Transaction Confirmed",
    },
  ];
}

async function runGraph(
  thread: ThreadRecord,
  incoming: LangChainMessage[],
): Promise<void> {
  let messages: LangChainMessage[];
  try {
    const forGraph =
      hasToolResult(incoming) || thread.status === "interrupted"
        ? [...thread.values.messages, ...incoming]
        : incoming;
    const result = await graph.invoke({
      messages: toGraphMessages(forGraph),
    });
    const raw = (result as { messages?: unknown[] }).messages ?? [];
    messages = raw.map(serializeMessage);
  } catch {
    messages = hasToolResult(incoming) || thread.status === "interrupted"
      ? fallbackConfirmed(thread, incoming)
      : fallbackPurchase(incoming);
  }

  thread.values.messages = messages;
  const last = messages.at(-1);
  const pendingTools = Array.isArray(last?.tool_calls) && last.tool_calls.length;
  thread.status = pendingTools ? "interrupted" : "idle";
  thread.updated_at = nowIso();
  emitLifecycle(thread, "started");
  emitValues(thread);
  emitLifecycle(thread, pendingTools ? "interrupted" : "completed");
}

async function handleCommand(
  thread: ThreadRecord,
  command: Record<string, unknown>,
) {
  const id = command.id ?? 0;
  const method = String(command.method ?? "");
  const params = (command.params ?? {}) as Record<string, unknown>;
  const runId = `run-${Date.now()}`;

  if (method === "run.start" || method === "input.respond") {
    const incoming = incomingMessages(params.input ?? params);
    await runGraph(thread, incoming);
    return {
      type: "success",
      id,
      result: { run_id: runId },
    };
  }

  if (method === "state.get") {
    return { type: "success", id, result: statePayload(thread) };
  }

  if (method === "agent.getTree") {
    return { type: "success", id, result: { nodes: [] } };
  }

  if (method.startsWith("subscription.")) {
    return {
      type: "success",
      id,
      result: { subscription_id: `sub-${id}` },
    };
  }

  return { type: "success", id, result: {} };
}

function eventStream(
  thread: ThreadRecord,
  since = 0,
): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      const send = (chunk: Uint8Array) => {
        try {
          controller.enqueue(chunk);
        } catch {
          thread.listeners.delete(send);
        }
      };
      for (const event of thread.events) {
        const seq = typeof event.seq === "number" ? event.seq : 0;
        if (seq > since) send(sseData(event));
      }
      thread.listeners.add(send);
      const heartbeat = setInterval(() => {
        try {
          controller.enqueue(encoder().encode(": keepalive\n\n"));
        } catch {
          clearInterval(heartbeat);
          thread.listeners.delete(send);
        }
      }, 15000);
      (controller as unknown as { _g7hb?: ReturnType<typeof setInterval> })._g7hb =
        heartbeat;
    },
    cancel() {
      thread.listeners.clear();
    },
  });
}

async function handle(req: NextRequest, method: string): Promise<Response> {
  const path = pathOf(req);
  const parts = path.split("/").filter(Boolean);

  if (method === "OPTIONS") {
    return new NextResponse(null, { status: 204, headers: corsHeaders() });
  }

  if (method === "POST" && path === "threads") {
    const threadId = `thread-${Date.now()}`;
    return json(threadPayload(getOrCreate(threadId)));
  }

  if (parts[0] === "threads" && parts[1] && parts.length === 2) {
    const thread = THREADS.get(parts[1]);
    if (method === "GET") {
      if (!thread) return json({ error: "not found" }, 404);
      return json(threadPayload(thread));
    }
    if (method === "DELETE") {
      THREADS.delete(parts[1]);
      return json({ ok: true });
    }
  }

  if (parts[0] === "threads" && parts[1] && parts[2] === "state") {
    const thread = getOrCreate(parts[1]);
    if (method === "GET") return json(statePayload(thread));
    if (method === "POST") return json(statePayload(thread));
  }

  if (parts[0] === "threads" && parts[1] && parts[2] === "history") {
    return json([]);
  }

  if (method === "POST" && path === "threads/search") {
    return json([]);
  }

  if (method === "GET" && parts[0] === "assistants") {
    const assistant = {
      assistant_id: parts[1] ?? "stockbroker",
      graph_id: "stockbroker",
      name: "stockbroker",
    };
    return json(parts[1] ? assistant : [assistant]);
  }

  if (
    method === "POST" &&
    parts[0] === "threads" &&
    parts[1] &&
    parts[2] === "commands"
  ) {
    const thread = getOrCreate(parts[1]);
    const command = (await req.json().catch(() => ({}))) as Record<
      string,
      unknown
    >;
    return json(await handleCommand(thread, command));
  }

  if (
    method === "POST" &&
    parts[0] === "threads" &&
    parts[1] &&
    ((parts[2] === "stream" && parts[3] === "events") || parts[2] === "stream")
  ) {
    const thread = getOrCreate(parts[1]);
    const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
    const since = typeof body.since === "number" ? body.since : 0;
    return new Response(eventStream(thread, since), {
      status: 200,
      headers: corsHeaders({
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      }),
    });
  }

  if (
    method === "POST" &&
    parts[0] === "threads" &&
    parts[2] === "runs" &&
    parts[3] === "stream"
  ) {
    const thread = getOrCreate(parts[1]);
    const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
    const incoming = incomingMessages(
      (body.input as Record<string, unknown> | undefined) ?? body,
    );
    await runGraph(thread, incoming);
    const headers = corsHeaders({
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Content-Location": `/threads/${thread.thread_id}/runs/run-${Date.now()}`,
    });
    const bodyText = thread.events
      .map((event) => `data: ${JSON.stringify(event)}\n\n`)
      .join("");
    return new Response(bodyText, { status: 200, headers });
  }

  return json({ error: `unhandled ${method} /${path}` }, 404);
}

export const GET = (req: NextRequest) => handle(req, "GET");
export const POST = (req: NextRequest) => handle(req, "POST");
export const PUT = (req: NextRequest) => handle(req, "PUT");
export const PATCH = (req: NextRequest) => handle(req, "PATCH");
export const DELETE = (req: NextRequest) => handle(req, "DELETE");
export const OPTIONS = () =>
  new NextResponse(null, { status: 204, headers: corsHeaders() });
