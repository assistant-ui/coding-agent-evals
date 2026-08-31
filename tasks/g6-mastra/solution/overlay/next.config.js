import { withAui } from "@assistant-ui/next";
/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [
    "@assistant-ui/react",
    "@assistant-ui/ai-sdk",
    "@assistant-ui/react-ai-sdk",
  ],
  serverExternalPackages: ["@mastra/*"],
};

export default withAui(nextConfig);
