# Task 7: Install and Configure shadcn/ui Components

**Status**: `completed`
**Blocked By**: #6 (Next.js Setup)
**Blocks**: #9, #10

## Objective

Set up shadcn/ui component library with all required components for the dashboard.

## Tasks

- [ ] Run `npx shadcn-ui@latest init`
- [ ] Install core components
- [ ] Configure component aliases
- [ ] Verify components work

## Initialize shadcn/ui

```bash
cd kite-dashboard
npx shadcn-ui@latest init
```

Configuration options:
- Style: Default
- Base color: Slate
- CSS variables: Yes
- tailwind.config.js location: tailwind.config.ts
- components.json location: components.json
- Utility functions location: src/lib/utils.ts
- React Server Components: Yes
- Write to components.json: Yes

## Install Components

```bash
# Core layout components
npx shadcn-ui@latest add card
npx shadcn-ui@latest add button
npx shadcn-ui@latest add separator
npx shadcn-ui@latest add scroll-area

# Navigation
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add sheet
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add toggle-group

# Data display
npx shadcn-ui@latest add table
npx shadcn-ui@latest add badge

# Forms
npx shadcn-ui@latest add select
npx shadcn-ui@latest add switch
npx shadcn-ui@latest add input

# Feedback
npx shadcn-ui@latest add skeleton
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add dialog

# Search
npx shadcn-ui@latest add command
```

Or install all at once:
```bash
npx shadcn-ui@latest add card button separator scroll-area dropdown-menu sheet tabs toggle-group table badge select switch input skeleton toast dialog command
```

## components.json

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/app/globals.css",
    "baseColor": "slate",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils"
  }
}
```

## src/lib/utils.ts

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number, currency = "INR"): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPercent(value: number, decimals = 2): string {
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(decimals)}%`;
}

export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: decimals,
  }).format(value);
}
```

## Install Additional Dependencies

```bash
npm install clsx tailwind-merge class-variance-authority lucide-react
npm install tailwindcss-animate
npm install @radix-ui/react-icons
```

## Component Directory Structure

After installation:
```
src/components/ui/
├── badge.tsx
├── button.tsx
├── card.tsx
├── command.tsx
├── dialog.tsx
├── dropdown-menu.tsx
├── input.tsx
├── scroll-area.tsx
├── select.tsx
├── separator.tsx
├── sheet.tsx
├── skeleton.tsx
├── switch.tsx
├── table.tsx
├── tabs.tsx
├── toast.tsx
├── toaster.tsx
├── toggle-group.tsx
└── use-toast.ts
```

## Install Recharts (for charts)

```bash
npm install recharts
```

## Verification

Create a test page `src/app/test/page.tsx`:

```tsx
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function TestPage() {
  return (
    <div className="p-8 space-y-4">
      <h1 className="text-2xl font-bold">Component Test</h1>

      <Card>
        <CardHeader>
          <CardTitle>Test Card</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Button>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="destructive">Destructive</Button>
          </div>
          <div className="mt-4 flex gap-2">
            <Badge>Default</Badge>
            <Badge variant="secondary">Secondary</Badge>
            <Badge variant="destructive">Error</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

Visit http://localhost:3000/test to verify components render correctly.

## Notes

- shadcn/ui components are copied to your codebase (not npm dependencies)
- Components can be customized directly in `src/components/ui/`
- Radix primitives provide accessibility out of the box
- All components support dark mode via CSS variables

---

*Last updated: February 2026*
