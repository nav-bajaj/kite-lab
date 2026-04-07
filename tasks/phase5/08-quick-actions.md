# Task 8: Quick Actions Component

**Status**: `pending`
**Blocked By**: #2, #14 (Job Endpoints, API Client)
**Blocks**: None

## Objective

Create a card grid with quick action buttons for common operations.

## Tasks

- [ ] Create `quick-actions.tsx` in `components/admin/`
- [ ] Implement action button cards
- [ ] Add loading states during execution
- [ ] Add success/error toast notifications
- [ ] Handle login modal for Kite OAuth

## Implementation

### File: `kite-dashboard/src/components/admin/quick-actions.tsx`

```tsx
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
import { useToast } from "@/components/ui/use-toast";
import { RefreshCw, BarChart3, Key, HardDrive, Loader2, ExternalLink } from "lucide-react";
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
];

export function QuickActions() {
  const [loading, setLoading] = useState<string | null>(null);
  const [loginOpen, setLoginOpen] = useState(false);
  const [loginUrl, setLoginUrl] = useState<string>("");
  const [loginInstructions, setLoginInstructions] = useState<string>("");
  const { toast } = useToast();

  const handleAction = async (action: QuickAction) => {
    if (action.special === "login") {
      // Fetch login URL and show modal
      try {
        const response = await getLoginUrl();
        setLoginUrl(response.url);
        setLoginInstructions(response.instructions);
        setLoginOpen(true);
      } catch (error) {
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
    } catch (error) {
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

      {/* Login Instructions Modal */}
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
```

## Action Cards

| Action | Command | Icon | Description |
|--------|---------|------|-------------|
| Daily Pipeline | `daily_pipeline` | RefreshCw | Fetch data, build signals, backup |
| Generate Portfolio | `generate_portfolio` | BarChart3 | Build momentum signals |
| Kite Login | (modal) | Key | Refresh API token |
| Backup Data | `backup_data` | HardDrive | Sync to external location |

## Loading States

```tsx
// Button shows spinner when loading
{isLoading ? (
  <Loader2 className="h-6 w-6 animate-spin" />
) : (
  <Icon className="h-6 w-6" />
)}

// All buttons disabled while any action is running
disabled={loading !== null}
```

## Toast Notifications

### Success
```tsx
toast({
  title: "Job Started",
  description: `${action.label} job created (ID: abc12345)`,
});
```

### Error
```tsx
toast({
  title: "Error",
  description: `Failed to start ${action.label}`,
  variant: "destructive",
});
```

## Login Modal

The Kite login requires browser interaction (OAuth). The modal shows:
1. Instructions for completing login
2. Link to open Zerodha login page
3. Steps to copy request token

```
┌────────────────────────────────────────┐
│ Kite Login Required                ✕   │
│ Follow these steps to refresh token    │
├────────────────────────────────────────┤
│                                        │
│ ┌────────────────────────────────────┐ │
│ │ 1. Open this URL in your browser   │ │
│ │ 2. Login with Zerodha credentials  │ │
│ │ 3. Copy 'request_token' from URL   │ │
│ │ 4. Run: python scripts/login...    │ │
│ └────────────────────────────────────┘ │
│                                        │
│ [        Open Zerodha Login         ]  │
│                                        │
└────────────────────────────────────────┘
```

## Responsive Grid

```tsx
// 2 columns on mobile, 4 columns on larger screens
<div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
```

| Screen | Columns |
|--------|---------|
| Mobile (<640px) | 2 |
| Tablet+ (640px+) | 4 |

## Verification

1. Click each quick action button
2. Loading spinner appears
3. Toast notification shows on completion
4. Kite Login opens modal with instructions
5. External link opens in new tab
6. Buttons disabled while loading

---

*Status Key: `pending` | `in_progress` | `completed`*
