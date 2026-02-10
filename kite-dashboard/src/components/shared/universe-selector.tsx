"use client";

import { useUniverse } from "@/contexts/universe-context";
import { UNIVERSE_IDS, UNIVERSES } from "@/lib/universes";
import { UniverseId } from "@/lib/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Globe } from "lucide-react";

export function UniverseSelector() {
  const { universeId, setUniverse, isLoading } = useUniverse();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground">
        <Globe className="h-4 w-4" />
        <span>Loading...</span>
      </div>
    );
  }

  return (
    <Select value={universeId} onValueChange={(v) => setUniverse(v as UniverseId)}>
      <SelectTrigger className="w-[140px]">
        <Globe className="mr-2 h-4 w-4" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {UNIVERSE_IDS.map((id) => {
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
