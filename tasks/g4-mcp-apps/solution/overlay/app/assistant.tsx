"use client";

import { useEffect, useState } from "react";
import {
  AssistantRuntimeProvider,
  AuiConfig,
  McpAppRenderer,
  McpAppsRemoteHost,
  Tools,
} from "@assistant-ui/react";
import { useChatRuntime, AssistantChatTransport } from "@assistant-ui/ai-sdk";
import { lastAssistantMessageIsCompleteWithToolCalls } from "ai";
import { McpManagerResource, defineConnector } from "@assistant-ui/react-mcp";
import { Thread } from "@/components/assistant-ui/thread";
import { McpConfigDialog } from "@/components/assistant-ui/mcp-config";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { ThreadListSidebar } from "@/components/assistant-ui/threadlist-sidebar";
import { Separator } from "@/components/ui/separator";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

const FALLBACK_MCP_URL = "http://127.0.0.1:8787/mcp";

export const Assistant = () => {
  const [mcpUrl, setMcpUrl] = useState(FALLBACK_MCP_URL);
  useEffect(() => {
    setMcpUrl(`${window.location.origin}/mcp`);
  }, []);

  const runtime = useChatRuntime({
    sendAutomaticallyWhen: lastAssistantMessageIsCompleteWithToolCalls,
    transport: new AssistantChatTransport({
      api: "/api/chat",
    }),
  });

  const config = AuiConfig({
    tools: Tools({
      mcpApp: McpAppRenderer({
        host: McpAppsRemoteHost({ url: "/api/mcp-apps" }),
        hostInfo: { name: "assistant-ui-starter-mcp", version: "0.1.0" },
      }),
    }),
    mcp: McpManagerResource({
      connectors: [
        defineConnector({
          id: "local-test",
          name: "Local test MCP",
          url: mcpUrl,
          auth: { type: "none" },
        }),
      ],
    }),
  });

  return (
    <AssistantRuntimeProvider config={config} runtime={runtime}>
      <SidebarProvider>
        <div className="flex h-dvh w-full pr-0.5">
          <ThreadListSidebar />
          <SidebarInset>
            <header className="flex h-16 shrink-0 items-center justify-between gap-2 border-b px-4">
              <div className="flex items-center gap-2">
                <SidebarTrigger />
                <Separator orientation="vertical" className="mr-2 h-4" />
                <Breadcrumb>
                  <BreadcrumbList>
                    <BreadcrumbItem className="hidden md:block">
                      <BreadcrumbLink
                        href="https://www.assistant-ui.com/docs/getting-started"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Build Your Own ChatGPT UX
                      </BreadcrumbLink>
                    </BreadcrumbItem>
                    <BreadcrumbSeparator className="hidden md:block" />
                    <BreadcrumbItem>
                      <BreadcrumbPage>Starter Template</BreadcrumbPage>
                    </BreadcrumbItem>
                  </BreadcrumbList>
                </Breadcrumb>
              </div>
              <McpConfigDialog />
            </header>
            <div className="flex-1 overflow-hidden">
              <Thread />
            </div>
          </SidebarInset>
        </div>
      </SidebarProvider>
    </AssistantRuntimeProvider>
  );
};
