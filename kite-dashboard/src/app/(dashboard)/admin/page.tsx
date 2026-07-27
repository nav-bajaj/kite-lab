"use client";

import { useState } from "react";
import {
  QuickActions,
  PortfolioGenerator,
  JobList,
  LogViewer,
  ScheduleTable,
  SystemStatus,
  FreshnessPanel,
  OptionsWorkerPanel,
} from "@/components/admin";

export default function AdminPage() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      {/* Page Header with System Status */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Admin Control Panel</h1>
          <p className="text-muted-foreground">
            Manage jobs, schedules, and system health
          </p>
        </div>
        <SystemStatus />
      </div>

      {/* Quick Actions */}
      <QuickActions />

      {/* Options data worker heartbeat (full width) */}
      <OptionsWorkerPanel />

      {/* Data freshness monitor (full width) */}
      <FreshnessPanel />

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left Column: Portfolio Generator */}
        <PortfolioGenerator />

        {/* Right Column: Job List */}
        <JobList
          onSelectJob={setSelectedJobId}
          selectedJobId={selectedJobId}
        />
      </div>

      {/* Log Viewer (Full Width) */}
      <LogViewer jobId={selectedJobId} />

      {/* Schedule Table (Full Width) */}
      <ScheduleTable />
    </div>
  );
}
