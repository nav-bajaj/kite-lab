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

// A small "Strategy" eyebrow stacked above the selected name, so the control
// reads as a labelled picker rather than a bare dropdown (or a floating word
// next to it).
const EYEBROW = "text-[10px] font-medium uppercase tracking-wider text-muted-foreground";

export function UniverseSelector() {
  const { universeId, setUniverse, isLoading, visibleUniverseIds } = useUniverse();

  if (isLoading) {
    return (
      <div className="flex flex-col items-start gap-0.5 rounded-md border px-3 py-1 leading-tight">
        <span className={EYEBROW}>Strategy</span>
        <span className="text-sm text-muted-foreground">Loading…</span>
      </div>
    );
  }

  // eslint-disable-next-line security/detect-object-injection -- universeId is a typed UniverseId literal, UNIVERSES is a closed Record
  const current = UNIVERSES[universeId];

  return (
    <Select value={universeId} onValueChange={(v) => setUniverse(v as UniverseId)}>
      {/* Two-line trigger: the "Strategy" eyebrow labels the control; the
          selected name sits below it. h-auto overrides the primitive's fixed
          h-9 so both lines fit. Stock count stays in the dropdown items. */}
      <SelectTrigger className="!h-auto py-1">
        <span className="flex flex-col items-start gap-0.5 text-left leading-tight">
          <span className={EYEBROW}>Strategy</span>
          <span className="text-sm font-medium">{current?.name}</span>
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
