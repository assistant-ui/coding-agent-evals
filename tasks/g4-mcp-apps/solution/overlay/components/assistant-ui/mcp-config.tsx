"use client";

import { type FC, type ReactNode, useState, isValidElement } from "react";
import { useAuiState } from "@assistant-ui/store";
import {
  McpAddFormPrimitive,
  McpManagerPrimitive,
  McpServerPrimitive,
  type MCPConnectionState,
} from "@assistant-ui/react-mcp";
import {
  Loader2Icon,
  PlugIcon,
  PlugZapIcon,
  PlusIcon,
  ServerIcon,
  ShieldAlertIcon,
  Trash2Icon,
  XIcon,
} from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

const inputClassName =
  "border-input h-9 w-full min-w-0 rounded-md border bg-transparent px-3 py-1 text-sm shadow-xs outline-none";

export namespace McpConfigDialog {
  export type Props = {
    children?: ReactNode;
  };
}

export const McpConfigDialog: FC<McpConfigDialog.Props> = ({ children }) => {
  return (
    <Dialog>
      {isValidElement(children) ? (
        <DialogTrigger render={children} />
      ) : (
        <DialogTrigger
          render={
            <Button
              variant="outline"
              size="sm"
              className="aui-mcp-config-trigger gap-2"
            />
          }
        >
          <PlugIcon className="size-4" />
          MCP servers
        </DialogTrigger>
      )}
      <DialogContent className="aui-mcp-config-content sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>MCP servers</DialogTitle>
          <DialogDescription>
            Connect to Model Context Protocol servers to expose their tools to
            this assistant.
          </DialogDescription>
        </DialogHeader>
        <McpManagerPrimitive.Root>
          <div className="flex flex-col gap-4">
            <ConnectorsSection />
            <Separator />
            <CustomServersSection />
          </div>
        </McpManagerPrimitive.Root>
      </DialogContent>
    </Dialog>
  );
};
McpConfigDialog.displayName = "McpConfigDialog";

const ConnectorsSection: FC = () => {
  return (
    <section className="aui-mcp-connectors flex flex-col gap-2">
      <SectionTitle>Connectors</SectionTitle>
      <div className="flex flex-col gap-2">
        <McpManagerPrimitive.Connectors>
          {() => <ServerCard />}
        </McpManagerPrimitive.Connectors>
      </div>
    </section>
  );
};

const CustomServersSection: FC = () => {
  const [showForm, setShowForm] = useState(false);
  return (
    <section className="aui-mcp-custom-servers flex flex-col gap-2">
      <SectionTitle>Custom servers</SectionTitle>
      <div className="flex flex-col gap-2">
        <McpManagerPrimitive.CustomServers>
          {() => <ServerCard />}
        </McpManagerPrimitive.CustomServers>
      </div>
      {!showForm && (
        <McpManagerPrimitive.AddCustomTrigger
          className={cn(
            buttonVariants({ variant: "outline" }),
            "aui-mcp-add-trigger h-9 justify-start gap-2 rounded-lg px-3 text-sm",
          )}
          onClick={() => setShowForm(true)}
        >
          <PlusIcon className="size-4" />
          Add server
        </McpManagerPrimitive.AddCustomTrigger>
      )}
      {showForm && <AddServerForm onClose={() => setShowForm(false)} />}
    </section>
  );
};

const SectionTitle: FC<{ children: ReactNode }> = ({ children }) => (
  <h3 className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
    {children}
  </h3>
);

const ServerCard: FC = () => {
  return (
    <McpServerPrimitive.Root
      className={cn(
        "aui-mcp-server-card flex flex-col gap-2 rounded-lg border p-3",
        "data-[connection-state=error]:border-destructive/40",
      )}
    >
      <div className="flex items-center gap-3">
        <div className="bg-muted text-muted-foreground flex size-8 shrink-0 items-center justify-center rounded-md border">
          <ServerIcon className="size-4" />
        </div>
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-sm font-medium">
            <McpServerPrimitive.Name />
          </span>
          <StatusLine />
        </div>
        <div className="flex items-center gap-1">
          <ServerActions />
          <McpServerPrimitive.RemoveButton
            className={cn(
              buttonVariants({ variant: "ghost", size: "icon" }),
              "aui-mcp-server-remove text-muted-foreground size-7",
            )}
          >
            <Trash2Icon className="size-4" />
            <span className="sr-only">Remove</span>
          </McpServerPrimitive.RemoveButton>
        </div>
      </div>
      <ServerError />
    </McpServerPrimitive.Root>
  );
};

const STATUS_LABEL: Record<MCPConnectionState, string> = {
  connected: "Connected",
  connecting: "Connecting…",
  authRequired: "Auth required",
  authPending: "Authorizing…",
  error: "Error",
  disconnected: "Disconnected",
};

const StatusLine: FC = () => {
  const status = useAuiState((s) => s.mcpServer.connectionState);
  const label = STATUS_LABEL[status];
  return (
    <div className="text-muted-foreground flex items-center gap-1.5 text-xs">
      <span className="inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5">
        {status === "connecting" && (
          <Loader2Icon className="size-3 animate-spin" />
        )}
        {label}
      </span>
    </div>
  );
};

const ServerError: FC = () => {
  const message = useAuiState((s) => s.mcpServer.lastError?.message ?? null);
  if (!message) return null;
  return (
    <div className="border-destructive/40 text-destructive flex items-start gap-2 rounded-md border px-2 py-1.5 text-xs">
      <ShieldAlertIcon className="mt-0.5 size-3.5 shrink-0" />
      <span className="break-words">{message}</span>
    </div>
  );
};

const ServerActions: FC = () => (
  <div className="flex flex-wrap gap-2">
    <McpServerPrimitive.ConnectButton
      className={cn(
        buttonVariants({ variant: "default", size: "sm" }),
        "aui-mcp-server-connect h-8 gap-2 text-xs",
      )}
    >
      <PlugZapIcon className="size-3.5" />
      Connect
    </McpServerPrimitive.ConnectButton>
    <McpServerPrimitive.OAuthLink
      className={cn(
        buttonVariants({ variant: "default", size: "sm" }),
        "aui-mcp-server-authorize h-8 gap-2 text-xs",
      )}
    >
      Authorize
    </McpServerPrimitive.OAuthLink>
    <McpServerPrimitive.DisconnectButton
      className={cn(
        buttonVariants({ variant: "outline", size: "sm" }),
        "aui-mcp-server-disconnect h-8 text-xs",
      )}
    >
      Disconnect
    </McpServerPrimitive.DisconnectButton>
  </div>
);

const AddServerForm: FC<{ onClose: () => void }> = ({ onClose }) => {
  return (
    <McpAddFormPrimitive.Root onSubmitted={onClose} onCancel={onClose}>
      <div className="aui-mcp-add-form flex flex-col gap-3 rounded-lg border p-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium">New server</h4>
          <McpAddFormPrimitive.Cancel
            type="button"
            className={cn(
              buttonVariants({ variant: "ghost", size: "icon" }),
              "text-muted-foreground size-7",
            )}
          >
            <XIcon className="size-4" />
            <span className="sr-only">Close</span>
          </McpAddFormPrimitive.Cancel>
        </div>
        <FormRow label="Name">
          <McpAddFormPrimitive.NameField
            placeholder="My MCP server"
            className={inputClassName}
          />
        </FormRow>
        <FormRow label="URL">
          <McpAddFormPrimitive.UrlField
            placeholder="https://example.com/mcp"
            className={inputClassName}
          />
        </FormRow>
        <FormRow label="Auth">
          <McpAddFormPrimitive.AuthSelect className="aui-mcp-auth-select bg-background h-9 w-full rounded-md border px-2 text-sm" />
          <McpAddFormPrimitive.AuthFields />
        </FormRow>
        <McpAddFormPrimitive.Error className="text-destructive text-xs" />
        <div className="flex justify-end gap-2">
          <McpAddFormPrimitive.Cancel
            type="button"
            className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
          >
            Cancel
          </McpAddFormPrimitive.Cancel>
          <McpAddFormPrimitive.Submit
            type="submit"
            className={cn(buttonVariants({ size: "sm" }))}
          >
            Add server
          </McpAddFormPrimitive.Submit>
        </div>
      </div>
    </McpAddFormPrimitive.Root>
  );
};

const FormRow: FC<{ label: string; children: ReactNode }> = ({
  label,
  children,
}) => (
  <div className="flex flex-col gap-1.5">
    <span className="text-xs">{label}</span>
    <div className="flex flex-col gap-2">{children}</div>
  </div>
);
