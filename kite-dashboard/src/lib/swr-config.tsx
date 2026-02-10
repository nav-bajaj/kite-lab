"use client";

import { SWRConfig } from "swr";
import { ReactNode } from "react";
import { toast } from "sonner";
import { ApiError } from "./api-client";

interface SWRProviderProps {
  children: ReactNode;
}

export function SWRProvider({ children }: SWRProviderProps) {
  return (
    <SWRConfig
      value={{
        onError: (error: Error) => {
          if (error instanceof ApiError) {
            if (error.status === 401) {
              toast.error("Session expired. Please sign in again.");
            } else if (error.status === 403) {
              toast.error("Access denied.");
            } else if (error.status >= 500) {
              toast.error("Server error. Please try again later.");
            } else {
              toast.error(error.message);
            }
          } else {
            toast.error("Failed to fetch data.");
          }
        },
        revalidateOnFocus: true,
        revalidateOnReconnect: true,
        shouldRetryOnError: (error: Error) => {
          // Don't retry on auth errors
          if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
            return false;
          }
          return true;
        },
        errorRetryCount: 3,
        dedupingInterval: 2000,
      }}
    >
      {children}
    </SWRConfig>
  );
}
