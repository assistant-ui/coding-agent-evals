"use client";

import {
  AssistantRuntimeProvider,
  AuiProvider,
  AuiConfig,
  Suggestions,
  Tools,
  unstable_Interactables,
  useAui,
} from "@assistant-ui/react";
import { useChatRuntime, AssistantChatTransport } from "@assistant-ui/ai-sdk";
import { lastAssistantMessageIsCompleteWithToolCalls } from "ai";
import { Thread } from "@/components/assistant-ui/thread";
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
import {
  ArtifactSurface,
  ArtifactSurfaceProvider,
  useArtifactSurface,
} from "./artifact-surface";
import toolkit from "./toolkit";

function ClaudeShell() {
  const { active } = useArtifactSurface();

  return (
    <SidebarProvider>
      <div className="flex h-dvh w-full pr-0.5">
        <ThreadListSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem className="hidden md:block">
                  <BreadcrumbLink
                    href="https://www.assistant-ui.com/examples/claude"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Build Your Own Claude UX
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="hidden md:block" />
                <BreadcrumbItem>
                  <BreadcrumbPage>Artifacts shell</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </header>
          <div className="flex min-h-0 flex-1 overflow-hidden">
            <section
              className={
                active
                  ? "bg-background hidden min-w-0 md:block md:w-[min(44vw,42rem)] md:shrink-0"
                  : "bg-background min-w-0 flex-1 md:max-w-[min(44vw,42rem)] md:shrink-0"
              }
            >
              <Thread />
            </section>
            <ArtifactSurface />
          </div>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}

function ArtifactScopes() {
  const aui = useAui();
  const config = AuiConfig({
    tools: Tools({ toolkit }),
    unstable_interactables: unstable_Interactables(),
    suggestions: Suggestions([
      {
        title: "Build a landing page",
        label: "with modern styling",
        prompt:
          "Build a beautiful landing page for a coffee shop with modern CSS.",
      },
      {
        title: "Create a calculator",
        label: "with HTML and JavaScript",
        prompt:
          "Create a calculator app with HTML, CSS, and JavaScript that supports basic arithmetic.",
      },
    ]),
  });

  return (
    <AuiProvider extends={aui} config={config}>
      <ArtifactSurfaceProvider>
        <ClaudeShell />
      </ArtifactSurfaceProvider>
    </AuiProvider>
  );
}

export const Assistant = () => {
  const runtime = useChatRuntime({
    sendAutomaticallyWhen: lastAssistantMessageIsCompleteWithToolCalls,
    transport: new AssistantChatTransport({
      api: "/api/chat",
    }),
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ArtifactScopes />
    </AssistantRuntimeProvider>
  );
};
