import { withAui } from "@assistant-ui/next";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/mcp",
        destination: "http://127.0.0.1:8787/mcp",
      },
      {
        source: "/mcp/:path*",
        destination: "http://127.0.0.1:8787/mcp/:path*",
      },
    ];
  },
};

export default withAui(nextConfig);
