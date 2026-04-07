# Task 14: API Client & Hooks

**Status**: `pending`
**Blocked By**: #2, #4, #6 (Backend endpoints)
**Blocks**: #8, #9, #10, #11, #12, #13 (Frontend components)

## Objective

Update API client with job, schedule, and system API functions. Add React hooks for data fetching.

## Tasks

- [ ] Update `lib/api-client.ts` with job functions
- [ ] Add schedule API functions
- [ ] Add system status API functions
- [ ] Update `lib/hooks.ts` with useJobs hook
- [ ] Add useSchedule hook
- [ ] Add useSystemStatus hook
- [ ] Add useJobLogs hook with SSE support

## Implementation

### File: `kite-dashboard/src/lib/api-client.ts` (additions)

```typescript
import { API_BASE_URL } from "./config";

// Types
export interface Job {
  id: string;
  command: string;
  label: string | null;
  universe: string | null;
  args: Record<string, any> | null;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  error_message: string | null;
  created_at: string;
}

export interface JobListResponse {
  jobs: Job[];
}

export interface CreateJobRequest {
  command: string;
  universe?: string;
  args?: Record<string, any>;
  label?: string;
}

export interface ScheduledJob {
  id: string;
  name: string;
  trigger: string;
  next_run: string | null;
  enabled: boolean;
}

export interface ScheduleListResponse {
  jobs: ScheduledJob[];
}

export interface CreateScheduleRequest {
  id: string;
  name: string;
  command: string;
  universe?: string;
  trigger: string;
  hour?: number;
  minute?: number;
  day_of_week?: string;
  hours?: number;
  minutes?: number;
}

export interface TokenStatus {
  valid: boolean;
  expires_at: string | null;
  message: string;
}

export interface DatabaseStatus {
  connected: boolean;
  latency_ms: number | null;
  message: string;
}

export interface SyncStatus {
  last_sync: string | null;
  last_data_date: string | null;
  message: string;
}

export interface SystemStatus {
  api_health: boolean;
  database: DatabaseStatus;
  token: TokenStatus;
  sync: SyncStatus;
  version: string;
  environment: string;
}

export interface JobLogsResponse {
  job_id: string;
  logs: string;
  status: string;
}

export interface LoginUrlResponse {
  url: string;
  instructions: string;
}

// Job API Functions
export async function createJob(request: CreateJobRequest): Promise<Job> {
  const response = await fetch(`${API_BASE_URL}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error("Failed to create job");
  }

  return response.json();
}

export async function getJobs(params?: {
  limit?: number;
  universe?: string;
  status?: string;
}): Promise<JobListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.universe) searchParams.set("universe", params.universe);
  if (params?.status) searchParams.set("status", params.status);

  const response = await fetch(
    `${API_BASE_URL}/api/jobs?${searchParams.toString()}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch jobs");
  }

  return response.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`);

  if (!response.ok) {
    throw new Error("Failed to fetch job");
  }

  return response.json();
}

export async function getJobLogs(
  jobId: string,
  tail?: number
): Promise<JobLogsResponse> {
  const params = tail ? `?tail=${tail}` : "";
  const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/logs${params}`);

  if (!response.ok) {
    throw new Error("Failed to fetch job logs");
  }

  return response.json();
}

export function getJobLogsStreamUrl(jobId: string): string {
  return `${API_BASE_URL}/api/jobs/${jobId}/logs?stream=true`;
}

export async function cancelJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/cancel`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Failed to cancel job");
  }
}

// Schedule API Functions
export async function getSchedule(): Promise<ScheduleListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/schedule`);

  if (!response.ok) {
    throw new Error("Failed to fetch schedule");
  }

  return response.json();
}

export async function createSchedule(
  request: CreateScheduleRequest
): Promise<ScheduledJob> {
  const response = await fetch(`${API_BASE_URL}/api/schedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw { response: { data: error } };
  }

  return response.json();
}

export async function deleteSchedule(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/schedule/${jobId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json();
    throw { response: { data: error } };
  }
}

export async function runScheduleNow(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/schedule/${jobId}/run`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Failed to run scheduled job");
  }
}

// System API Functions
export async function getSystemStatus(): Promise<SystemStatus> {
  const response = await fetch(`${API_BASE_URL}/api/system/status`);

  if (!response.ok) {
    throw new Error("Failed to fetch system status");
  }

  return response.json();
}

export async function getTokenStatus(): Promise<TokenStatus> {
  const response = await fetch(`${API_BASE_URL}/api/system/token`);

  if (!response.ok) {
    throw new Error("Failed to fetch token status");
  }

  return response.json();
}

export async function getLoginUrl(): Promise<LoginUrlResponse> {
  const response = await fetch(`${API_BASE_URL}/api/system/login-url`);

  if (!response.ok) {
    throw new Error("Failed to fetch login URL");
  }

  return response.json();
}
```

### File: `kite-dashboard/src/lib/hooks.ts` (additions)

```typescript
import useSWR from "swr";
import {
  getJobs,
  getJob,
  getJobLogs,
  getSchedule,
  getSystemStatus,
  JobListResponse,
  Job,
  JobLogsResponse,
  ScheduleListResponse,
  SystemStatus,
} from "./api-client";

// Job Hooks
export function useJobs(params?: {
  limit?: number;
  universe?: string;
  status?: string;
  refreshInterval?: number;
}) {
  return useSWR<JobListResponse>(
    ["jobs", params?.limit, params?.universe, params?.status],
    () => getJobs(params),
    {
      refreshInterval: params?.refreshInterval || 5000, // Refresh every 5s
      revalidateOnFocus: true,
    }
  );
}

export function useJob(jobId: string | null) {
  return useSWR<Job>(
    jobId ? ["job", jobId] : null,
    () => getJob(jobId!),
    {
      refreshInterval: 2000, // Refresh every 2s for running jobs
    }
  );
}

export function useJobLogs(jobId: string | null, tail?: number) {
  return useSWR<JobLogsResponse>(
    jobId ? ["job-logs", jobId, tail] : null,
    () => getJobLogs(jobId!, tail),
    {
      refreshInterval: 2000, // Refresh while viewing
      revalidateOnFocus: false,
    }
  );
}

// Schedule Hooks
export function useSchedule() {
  return useSWR<ScheduleListResponse>(
    "schedule",
    getSchedule,
    {
      refreshInterval: 30000, // Refresh every 30s
    }
  );
}

// System Hooks
export function useSystemStatus() {
  return useSWR<SystemStatus>(
    "system-status",
    getSystemStatus,
    {
      refreshInterval: 30000, // Refresh every 30s
      revalidateOnFocus: true,
    }
  );
}
```

## API Functions

### Jobs

| Function | Method | Endpoint |
|----------|--------|----------|
| `createJob` | POST | `/api/jobs` |
| `getJobs` | GET | `/api/jobs` |
| `getJob` | GET | `/api/jobs/{id}` |
| `getJobLogs` | GET | `/api/jobs/{id}/logs` |
| `cancelJob` | POST | `/api/jobs/{id}/cancel` |

### Schedule

| Function | Method | Endpoint |
|----------|--------|----------|
| `getSchedule` | GET | `/api/schedule` |
| `createSchedule` | POST | `/api/schedule` |
| `deleteSchedule` | DELETE | `/api/schedule/{id}` |
| `runScheduleNow` | POST | `/api/schedule/{id}/run` |

### System

| Function | Method | Endpoint |
|----------|--------|----------|
| `getSystemStatus` | GET | `/api/system/status` |
| `getTokenStatus` | GET | `/api/system/token` |
| `getLoginUrl` | GET | `/api/system/login-url` |

## SWR Hooks

### useJobs

Fetches job list with auto-refresh.

```tsx
const { data, isLoading, error, mutate } = useJobs({
  limit: 20,
  refreshInterval: 5000,
});
```

### useJob

Fetches single job details.

```tsx
const { data: job } = useJob(jobId);
```

### useJobLogs

Fetches job logs.

```tsx
const { data: logsData } = useJobLogs(jobId);
```

### useSchedule

Fetches scheduled jobs.

```tsx
const { data, mutate } = useSchedule();
```

### useSystemStatus

Fetches system status.

```tsx
const { data: status, mutate } = useSystemStatus();
```

## Refresh Intervals

| Hook | Interval | Reason |
|------|----------|--------|
| useJobs | 5s | Track running jobs |
| useJob | 2s | Monitor single job |
| useJobLogs | 2s | Live log updates |
| useSchedule | 30s | Schedules rarely change |
| useSystemStatus | 30s | Status rarely changes |

## SSE Streaming

For live log streaming:

```tsx
// Get SSE URL
const url = getJobLogsStreamUrl(jobId);

// Create EventSource
const eventSource = new EventSource(url);

eventSource.onmessage = (event) => {
  // Append new log line
  setLogs((prev) => prev + event.data + "\n");
};

eventSource.addEventListener("done", () => {
  eventSource.close();
});
```

## Error Handling

```tsx
try {
  const job = await createJob({ command: "daily_pipeline" });
} catch (error) {
  // Handle error
  toast({
    title: "Error",
    description: "Failed to create job",
    variant: "destructive",
  });
}
```

## Verification

1. All API functions work with backend
2. SWR hooks auto-refresh correctly
3. Error states handled properly
4. SSE streaming connects
5. Mutations trigger revalidation

---

*Status Key: `pending` | `in_progress` | `completed`*
