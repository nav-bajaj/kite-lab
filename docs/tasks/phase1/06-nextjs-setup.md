# Task 6: Set up Next.js Frontend Project with TypeScript

**Status**: `completed`
**Blocked By**: None
**Blocks**: #7, #8, #11

## Objective

Initialize the Next.js frontend project with TypeScript and Tailwind CSS.

## Tasks

- [ ] Create `kite-dashboard/` with `create-next-app`
- [ ] Configure `tailwind.config.js` for shadcn/ui
- [ ] Set up `globals.css` with CSS variables (light/dark mode)
- [ ] Create `lib/types.ts` for TypeScript interfaces
- [ ] Set up project structure

## Create Project

```bash
cd /Users/navdeep/kite-lab
npx create-next-app@latest kite-dashboard --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
```

Options:
- TypeScript: Yes
- ESLint: Yes
- Tailwind CSS: Yes
- `src/` directory: Yes
- App Router: Yes
- Import alias: @/*

## Directory Structure

```
kite-dashboard/
├── src/
│   ├── app/
│   │   ├── (dashboard)/        # Dashboard routes (protected)
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx        # Portfolio overview
│   │   │   ├── performance/
│   │   │   ├── trades/
│   │   │   ├── rebalance/
│   │   │   └── admin/
│   │   ├── api/
│   │   │   └── auth/
│   │   │       └── [...nextauth]/
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── layout.tsx          # Root layout
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── shared/             # Shared components
│   │   ├── portfolio/
│   │   ├── performance/
│   │   ├── trades/
│   │   ├── rebalance/
│   │   └── admin/
│   ├── hooks/
│   │   └── use-portfolio.ts
│   ├── lib/
│   │   ├── api-client.ts
│   │   ├── types.ts
│   │   ├── universes.ts
│   │   ├── universe-context.tsx
│   │   └── utils.ts
│   └── middleware.ts
├── public/
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── .env.local
```

## tailwind.config.ts

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
```

## src/app/globals.css

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

## src/lib/types.ts

```typescript
// Universe types
export type UniverseId = "nse500" | "nifty250" | "nifty100";

export interface Universe {
  id: UniverseId;
  name: string;
  description: string;
  stocks: number;
  riskProfile: string;
}

// Portfolio types
export interface Portfolio {
  total_value: number;
  cash: number;
  invested: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  total_return: number;
  total_return_pct: number;
  holdings_count: number;
  as_of_date: string;
}

export interface Holding {
  symbol: string;
  shares: number;
  avg_cost: number;
  current_price: number;
  notional: number;
  pnl: number;
  pnl_pct: number;
  weight: number;
  entry_date: string;
  holding_days: number;
  rank: number;
}

// Metrics types
export interface Metrics {
  period: {
    start: string;
    end: string;
    days: number;
  };
  returns: {
    total_return: number;
    cagr: number;
    mtd: number;
    ytd: number;
  };
  risk: {
    max_drawdown: number;
    max_dd_duration: number;
    volatility: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    calmar_ratio: number;
  };
  activity: {
    total_trades: number;
    avg_turnover: number;
    annualized_turnover: number;
    avg_holding_days: number;
    hit_rate: number;
  };
}

// Trade types
export interface Trade {
  id: number;
  date: string;
  symbol: string;
  side: "BUY" | "SELL";
  shares: number;
  price: number;
  notional: number;
  slippage: number;
}

// Job types
export interface Job {
  id: string;
  command: string;
  universe?: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  started_at?: string;
  ended_at?: string;
  duration_seconds?: number;
  error_message?: string;
}

// API response types
export interface ApiResponse<T> {
  data: T;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total_count: number;
  limit: number;
  offset: number;
}
```

## .env.local

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-32-character-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## Verification

```bash
cd kite-dashboard
npm run dev
# Visit http://localhost:3000
```

## Notes

- Using App Router (not Pages Router)
- `src/` directory for cleaner organization
- Import alias `@/*` maps to `src/*`
- shadcn/ui will be configured in Task #7

---

*Last updated: February 2026*
