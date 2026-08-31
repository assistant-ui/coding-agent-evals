export const maxDuration = 30;

const MCP_APP_MIME = "text/html;profile=mcp-app";
const SAMPLE_URI = "ui://sample/widget.html";

const SAMPLE_HTML = `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Sample MCP App</title>
    <style>
      body { font-family: system-ui, sans-serif; margin: 16px; }
    </style>
  </head>
  <body>
    <h1>Sample MCP App</h1>
    <p>This is a labeled sample MCP App widget.</p>
  </body>
</html>`;

export async function POST(req: Request) {
  let body: { method?: unknown; params?: Record<string, unknown> } = {};
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const method = body.method;
  const params = (body.params ?? {}) as Record<string, unknown>;
  if (typeof method !== "string") {
    return Response.json({ error: "Missing method" }, { status: 400 });
  }

  switch (method) {
    case "mcp-apps/read-resource": {
      if (typeof params.uri !== "string") {
        return Response.json({ error: "Missing uri" }, { status: 400 });
      }
      const html = params.uri.startsWith("ui://") ? SAMPLE_HTML : "";
      return Response.json({
        uri: params.uri || SAMPLE_URI,
        mimeType: MCP_APP_MIME,
        html,
      });
    }
    case "tools/call":
      return Response.json({
        content: [{ type: "text", text: "Sample MCP app tool result" }],
      });
    case "resources/read": {
      if (typeof params.uri !== "string") {
        return Response.json({ error: "Missing uri" }, { status: 400 });
      }
      return Response.json({
        contents: [
          {
            uri: params.uri,
            mimeType: MCP_APP_MIME,
            text: SAMPLE_HTML,
          },
        ],
      });
    }
    case "resources/list":
      return Response.json({
        resources: [{ uri: SAMPLE_URI, mimeType: MCP_APP_MIME }],
      });
    default:
      return Response.json({ error: "Unsupported method" }, { status: 400 });
  }
}
