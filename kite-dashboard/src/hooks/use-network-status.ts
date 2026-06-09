"use client";

import { useEffect, useState } from "react";

export interface NetworkStatus {
  saveData: boolean;
  effectiveType: string | null;
  // True on data-saver or 2g/slow-2g — callers should back off polling.
  isSlow: boolean;
}

type ConnectionLike = {
  saveData?: boolean;
  effectiveType?: string;
  addEventListener?: (type: "change", cb: () => void) => void;
  removeEventListener?: (type: "change", cb: () => void) => void;
};

function getConnection(): ConnectionLike | undefined {
  if (typeof navigator === "undefined") return undefined;
  return (navigator as Navigator & { connection?: ConnectionLike }).connection;
}

function readStatus(): NetworkStatus {
  const conn = getConnection();
  const effectiveType = conn?.effectiveType ?? null;
  const saveData = conn?.saveData ?? false;
  const isSlow =
    saveData || effectiveType === "2g" || effectiveType === "slow-2g";
  return { saveData, effectiveType, isSlow };
}

// Progressive enhancement around the Network Information API (Chromium-only;
// elsewhere it reports a fast connection and nothing changes). Lets callers
// throttle polling on metered / slow mobile connections.
export function useNetworkStatus(): NetworkStatus {
  const [status, setStatus] = useState<NetworkStatus>(readStatus);

  useEffect(() => {
    const conn = getConnection();
    if (!conn?.addEventListener) return;
    const update = () => setStatus(readStatus());
    conn.addEventListener("change", update);
    return () => conn.removeEventListener?.("change", update);
  }, []);

  return status;
}
