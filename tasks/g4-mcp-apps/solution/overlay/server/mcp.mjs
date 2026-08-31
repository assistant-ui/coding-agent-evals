/**
 * Local Streamable HTTP MCP server. One tool, `echo`.
 * Harbor / gold-lab: npm run start:mcp (port 8787).
 */
import express from "express";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

const PORT = Number(process.env.MCP_PORT ?? 8787);
const HOST = process.env.MCP_HOST ?? "127.0.0.1";

function buildServer() {
  const server = new McpServer({ name: "gold-echo", version: "0.0.1" });
  server.registerTool(
    "echo",
    {
      title: "Echo",
      description: "Echo back the provided text.",
      inputSchema: { text: z.string().describe("Text to echo back") },
    },
    async ({ text }) => ({
      content: [{ type: "text", text: `echo: ${text}` }],
    }),
  );
  return server;
}

const app = express();
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Authorization, Content-Type, Accept, Mcp-Session-Id, mcp-protocol-version",
  );
  res.setHeader("Access-Control-Expose-Headers", "Mcp-Session-Id");
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  next();
});
app.use(express.json({ type: ["application/json", "application/*+json"] }));

app.post("/mcp", async (req, res) => {
  try {
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
    });
    res.on("close", () => transport.close());
    const server = buildServer();
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (err) {
    console.error("MCP request error:", err);
    if (!res.headersSent) res.status(500).end();
  }
});

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.listen(PORT, HOST, () => {
  console.log(`MCP echo server http://${HOST}:${PORT}/mcp`);
});
