"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { RefreshCw, BarChart3, Key, HardDrive, Loader2, ExternalLink, Database } from "lucide-react";
import { createJob, getLoginUrl } from "@/lib/api-client";

interface QuickAction {
  id: string;
  label: string;
  description: string;
  icon: React.ElementType;
  command?: string;
  special?: "login";
}

const actions: QuickAction[] = [
  {
    id: "daily_pipeline",
    label: "Daily Pipeline",
    description: "Fetch data, build signals, backup",
    icon: RefreshCw,
    command: "daily_pipeline",
  },
  {
    id: "generate",
    label: "Generate Portfolio",
    description: "Build momentum signals",
    icon: BarChart3,
    command: "generate_portfolio",
  },
  {
    id: "login",
    label: "Kite Login",
    description: "Refresh API token",
    icon: Key,
    special: "login",
  },
  {
    id: "backup",
    label: "Backup Data",
    description: "Sync to external location",
    icon: HardDrive,
    command: "backup_data",
  },
  {
    id: "sync_db",
    label: "Sync Database",
    description: "Load CSV to database",
    icon: Database,
    command: "sync_database",
  },
];

export function QuickActions() {
  const [loading, setLoading] = useState<string | null>(null);
  const [loginOpen, setLoginOpen] = useState(false);
  const [loginUrl, setLoginUrl] = useState<string>("");
  const [loginInstructions, setLoginInstructions] = useState<string>("");
  const { toast } = useToast();

  const handleAction = async (action: QuickAction) => {
    if (action.special === "login") {
      try {
        const response = await getLoginUrl();
        setLoginUrl(response.url);
        setLoginInstructions(response.instructions);
        setLoginOpen(true);
      } catch {
        toast({
          title: "Error",
          description: "Failed to get login URL",
          variant: "destructive",
        });
      }
      return;
    }

    if (!action.command) return;

    setLoading(action.id);

    try {
      const job = await createJob({
        command: action.command,
        label: action.label,
      });

      toast({
        title: "Job Started",
        description: `${action.label} job created (ID: ${job.id.slice(0, 8)})`,
      });
    } catch {
      toast({
        title: "Error",
        description: `Failed to start ${action.label}`,
        variant: "destructive",
      });
    } finally {
      setLoading(null);
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {actions.map((action) => {
              const Icon = action.icon;
              const isLoading = loading === action.id;

              return (
                <Button
                  key={action.id}
                  variant="outline"
                  className="h-auto flex-col gap-2 p-4"
                  onClick={() => handleAction(action)}
                  disabled={loading !== null}
                >
                  {isLoading ? (
                    <Loader2 className="h-6 w-6 animate-spin" />
                  ) : (
                    <Icon className="h-6 w-6" />
                  )}
                  <div className="text-center">
                    <div className="font-medium">{action.label}</div>
                    <div className="text-xs text-muted-foreground">
                      {action.description}
                    </div>
                  </div>
                </Button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Dialog open={loginOpen} onOpenChange={setLoginOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Kite Login Required</DialogTitle>
            <DialogDescription>
              Follow these steps to refresh your API token
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="rounded-md bg-muted p-4">
              <pre className="whitespace-pre-wrap text-sm">
                {loginInstructions}
              </pre>
            </div>

            {loginUrl && (
              <Button asChild className="w-full">
                <a href={loginUrl} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Open Zerodha Login
                </a>
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
