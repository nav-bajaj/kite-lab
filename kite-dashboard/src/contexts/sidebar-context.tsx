"use client";

import { createContext, useContext, useState, ReactNode } from "react";

interface SidebarContextValue {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
  toggle: () => void;
}

const SidebarContext = createContext<SidebarContextValue | null>(null);

/**
 * Holds the desktop sidebar collapsed/expanded state at the dashboard layout
 * level so both the sidebar and the main content column read the same value —
 * the content's left offset (lg:pl-64 vs lg:pl-16) has to track the sidebar
 * width, otherwise collapsing leaves a dead gap. Lives in the layout, which
 * doesn't remount on route changes, so the choice persists while navigating
 * the dashboard.
 */
export function SidebarProvider({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <SidebarContext.Provider
      value={{ collapsed, setCollapsed, toggle: () => setCollapsed((v) => !v) }}
    >
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const ctx = useContext(SidebarContext);
  if (!ctx) {
    throw new Error("useSidebar must be used within a SidebarProvider");
  }
  return ctx;
}
