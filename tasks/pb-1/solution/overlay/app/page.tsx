"use client";

import { Thread } from "@/components/assistant-ui/thread";
import {
  AssistantRuntimeProvider,
  useAui,
  AuiProvider,
  AuiConfig,
  Suggestions,
  useRemoteThreadListRuntime,
} from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";
import { useEffect, useMemo, useState } from "react";
import { createBrowserThreadListAdapter } from "@/lib/browser-thread-list-adapter";

const LAST_THREAD_KEY = "pb-1-gold:last-thread";

function ThreadWithSuggestions() {
  const aui = useAui();
  const config = AuiConfig({
    suggestions: Suggestions([
      {
        title: "What's the weather",
        label: "in Tokyo right now?",
        prompt: "What's the weather in Tokyo?",
      },
      {
        title: "Tell me a fun fact",
        label: "about any topic",
        prompt: "Tell me a fun fact about space.",
      },
    ]),
  });
  return (
    <AuiProvider extends={aui} config={config}>
      <Thread />
    </AuiProvider>
  );
}

function ChatApp({ initialThreadId }: { initialThreadId?: string }) {
  const adapter = useMemo(
    () => createBrowserThreadListAdapter("pb-1-gold:"),
    [],
  );
  const runtime = useRemoteThreadListRuntime({
    runtimeHook: function GoldChatRuntime() {
      return useChatRuntime();
    },
    adapter,
    initialThreadId,
    onThreadIdChange: (threadId) => {
      if (threadId) {
        window.localStorage.setItem(LAST_THREAD_KEY, threadId);
      }
    },
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="h-full">
        <ThreadWithSuggestions />
      </div>
    </AssistantRuntimeProvider>
  );
}

export default function Home() {
  const [ready, setReady] = useState(false);
  const [initialThreadId, setInitialThreadId] = useState<string | undefined>();

  useEffect(() => {
    setInitialThreadId(
      window.localStorage.getItem(LAST_THREAD_KEY) ?? undefined,
    );
    setReady(true);
  }, []);

  if (!ready) {
    return <div className="h-full" />;
  }

  return <ChatApp initialThreadId={initialThreadId} />;
}
