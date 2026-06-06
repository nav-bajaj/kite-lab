"use client";

import { useUniverse } from "@/contexts/universe-context";
import { UNIVERSES } from "@/lib/universes";
import { UniverseId } from "@/lib/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { Globe } from "lucide-react";

export function UniverseSelector() {
  const { universeId, setUniverse, isLoading, visibleUniverseIds } = useUniverse();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground">
        <Globe className="h-4 w-4" />
        <span>Loading...</span>
      </div>
    );
  }

  // eslint-disable-next-line security/detect-object-injection -- universeId is a typed UniverseId literal, UNIVERSES is a closed Record
  const current = UNIVERSES[universeId];

  return (
    <Select value={universeId} onValueChange={(v) => setUniverse(v as UniverseId)}>
      {/* Single-line full name in the trigger — the two-line item markup was
          clipping the name + stock count in the short trigger. The trigger
          sizes to its content so the chevron sits next to the name; the stock
          count stays in the dropdown items below. */}
      <SelectTrigger>
        <span className="flex items-center gap-2">
          <Globe className="h-4 w-4 shrink-0" />
          <span>{current?.name}</span>
        </span>
      </SelectTrigger>
      {/* popper + align end: anchor the menu under the trigger. The default
          item-aligned positioning placed this top-right menu off-screen. */}
      <SelectContent position="popper" align="end" sideOffset={6}>
        {visibleUniverseIds.map((id) => {
          // eslint-disable-next-line security/detect-object-injection -- id is a typed UniverseId from a closed list
          const u = UNIVERSES[id];
          return (
            <SelectItem key={id} value={id}>
              <div className="flex flex-col">
                <span>{u.name}</span>
                <span className="text-xs text-muted-foreground">
                  {u.stocks} stocks
                </span>
              </div>
            </SelectItem>
          );
        })}
      </SelectContent>
    </Select>
  );
}
