"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { RefreshCw, BarChart3, Key, KeyRound, HardDrive, DatabaseZap, Loader2 } from "lucide-react";
import { createJob, getLoginUrl, headlessLogin } from "@/lib/api-client";

interface QuickAction {
  id: string;
  label: string;
  description: string;
  icon: React.ElementType;
  command?: string;
  args?: Record<string, unknown>;
  special?: "login" | "headless-login";
}

const actions: QuickAction[] = [
  {
    id: "daily_pipeline",
    label: "Daily Pipeline",
    description: "Auto-login + fetch, signals, backup",
    icon: RefreshCw,
    command: "daily_pipeline",
    args: { "with-login": true, "headless": true },
  },
  {
    id: "update_portfolios",
    label: "Update Portfolios",
    description: "Refresh prices & rebuild all 3",
    icon: BarChart3,
    command: "update_portfolios",
  },
  {
    id: "headless_login",
    label: "Auto Login",
    description: "Headless token refresh",
    icon: KeyRound,
    special: "headless-login",
  },
  {
    id: "login",
    label: "Browser Login",
    description: "Manual browser login",
    icon: Key,
    special: "login",
  },
  {
    id: "sync_database",
    label: "Sync to DB",
    description: "Push CSV data to database",
    icon: DatabaseZap,
    command: "sync_database",
  },
  {
    id: "backup",
    label: "Backup Data",
    description: "Sync to external location",
    icon: HardDrive,
    command: "backup_data",
  },
];

export function QuickActions() {
  const [loading, setLoading] = useState<string | null>(null);
  const { toast } = useToast();

  const handleAction = async (action: QuickAction) => {
    if (action.special === "headless-login") {
      setLoading(action.id);
      try {
        const result = await headlessLogin();
        toast({
          title: result.valid ? "Login Successful" : "Login Failed",
          description: result.message,
          variant: result.valid ? "default" : "destructive",
        });
      } catch {
        toast({
          title: "Error",
          description: "Headless login failed — check server env vars",
          variant: "destructive",
        });
      } finally {
        setLoading(null);
      }
      return;
    }

    if (action.special === "login") {
      setLoading(action.id);
      try {
        const response = await getLoginUrl();
        if (!response.url) {
          toast({
            title: "Error",
            description: "Kite API key not configured on server",
            variant: "destructive",
          });
          return;
        }
        // Open Zerodha login - callback handles token exchange automatically
        window.open(response.url, "_blank");
      } catch {
        toast({
          title: "Error",
          description: "Failed to get login URL",
          variant: "destructive",
        });
      } finally {
        setLoading(null);
      }
      return;
    }

    if (!action.command) return;

    setLoading(action.id);

    try {
      const job = await createJob({
        command: action.command,
        label: action.label,
        args: action.args,
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
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">
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
  );
}
