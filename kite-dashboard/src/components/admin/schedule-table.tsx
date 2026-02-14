"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Plus, Play, Trash2, Loader2, Clock } from "lucide-react";
import { useSchedule } from "@/lib/hooks";
import { createSchedule, deleteSchedule, runScheduleNow } from "@/lib/api-client";
import { formatDistanceToNow } from "date-fns";

interface NewScheduleForm {
  id: string;
  name: string;
  command: string;
  universe: string;
  hour: number;
  minute: number;
  dayOfWeek: string;
}

const defaultForm: NewScheduleForm = {
  id: "",
  name: "",
  command: "daily_pipeline",
  universe: "",
  hour: 7,
  minute: 0,
  dayOfWeek: "mon-fri",
};

const commands = [
  { value: "daily_pipeline", label: "Daily Pipeline" },
  { value: "generate_portfolio", label: "Generate Portfolio" },
  { value: "backup_data", label: "Backup Data" },
  { value: "fetch_prices", label: "Fetch Prices" },
];

const dayOptions = [
  { value: "", label: "Every day" },
  { value: "mon-fri", label: "Weekdays (Mon-Fri)" },
  { value: "sun", label: "Sunday" },
  { value: "sat", label: "Saturday" },
  { value: "mon", label: "Monday" },
];

export function ScheduleTable() {
  const { data, isLoading, mutate } = useSchedule();
  const [addOpen, setAddOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [form, setForm] = useState<NewScheduleForm>(defaultForm);
  const [submitting, setSubmitting] = useState(false);
  const { toast } = useToast();

  const handleAdd = async () => {
    if (!form.id || !form.name) {
      toast({
        title: "Error",
        description: "ID and Name are required",
        variant: "destructive",
      });
      return;
    }

    setSubmitting(true);

    try {
      await createSchedule({
        id: form.id,
        name: form.name,
        command: form.command,
        universe: form.universe || undefined,
        trigger: "cron",
        hour: form.hour,
        minute: form.minute,
        day_of_week: form.dayOfWeek || undefined,
      });

      toast({
        title: "Schedule Created",
        description: `${form.name} added to schedule`,
      });

      setAddOpen(false);
      setForm(defaultForm);
      mutate();
    } catch {
      toast({
        title: "Error",
        description: "Failed to create schedule",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteSchedule(id);

      toast({
        title: "Schedule Deleted",
        description: "Job removed from schedule",
      });

      setDeleteId(null);
      mutate();
    } catch {
      toast({
        title: "Error",
        description: "Cannot delete default scheduled tasks",
        variant: "destructive",
      });
      setDeleteId(null);
    }
  };

  const handleRunNow = async (id: string) => {
    setRunningId(id);

    try {
      await runScheduleNow(id);

      toast({
        title: "Job Triggered",
        description: "Scheduled job started immediately",
      });
    } catch {
      toast({
        title: "Error",
        description: "Failed to trigger job",
        variant: "destructive",
      });
    } finally {
      setRunningId(null);
    }
  };

  const formatNextRun = (nextRun: string | null) => {
    if (!nextRun) return "Not scheduled";

    return formatDistanceToNow(new Date(nextRun), { addSuffix: true });
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Scheduled Jobs</CardTitle>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Schedule
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Scheduled Job</DialogTitle>
              <DialogDescription>
                Create a new scheduled task
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="id">Job ID</Label>
                  <Input
                    id="id"
                    placeholder="my_schedule"
                    value={form.id}
                    onChange={(e) => setForm({ ...form, id: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    placeholder="My Schedule"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="command">Command</Label>
                <Select
                  value={form.command}
                  onValueChange={(value) => setForm({ ...form, command: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {commands.map((cmd) => (
                      <SelectItem key={cmd.value} value={cmd.value}>
                        {cmd.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="universe">Universe (optional)</Label>
                <Select
                  value={form.universe}
                  onValueChange={(value) => setForm({ ...form, universe: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="All universes" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All universes</SelectItem>
                    <SelectItem value="nse500">NSE 500</SelectItem>
                    <SelectItem value="nifty250">Nifty 250</SelectItem>
                    <SelectItem value="nifty100">Nifty 100</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="hour">Hour (0-23)</Label>
                  <Input
                    id="hour"
                    type="number"
                    min={0}
                    max={23}
                    value={form.hour}
                    onChange={(e) => setForm({ ...form, hour: parseInt(e.target.value) })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="minute">Minute (0-59)</Label>
                  <Input
                    id="minute"
                    type="number"
                    min={0}
                    max={59}
                    value={form.minute}
                    onChange={(e) => setForm({ ...form, minute: parseInt(e.target.value) })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="day">Days</Label>
                  <Select
                    value={form.dayOfWeek}
                    onValueChange={(value) => setForm({ ...form, dayOfWeek: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {dayOptions.map((day) => (
                        <SelectItem key={day.value} value={day.value}>
                          {day.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setAddOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleAdd} disabled={submitting}>
                {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Add Schedule
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : !data?.jobs?.length ? (
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
            <Clock className="mb-2 h-8 w-8" />
            <p>No scheduled jobs</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Schedule</TableHead>
                <TableHead>Next Run</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.jobs.map((job) => (
                <TableRow key={job.id}>
                  <TableCell className="font-medium">{job.name}</TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {job.trigger}
                  </TableCell>
                  <TableCell>
                    {formatNextRun(job.next_run)}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRunNow(job.id)}
                        disabled={runningId === job.id}
                        title="Run now"
                      >
                        {runningId === job.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Play className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeleteId(job.id)}
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Schedule?</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove the scheduled job. The action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteId && handleDelete(deleteId)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
