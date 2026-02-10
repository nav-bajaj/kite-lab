import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdminPage() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Admin Panel</CardTitle>
          <CardDescription>
            System configuration and job management
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 text-muted-foreground">
            <p>Admin panel will be implemented in Phase 4</p>
            <p className="text-sm mt-2">
              Manage pipeline jobs, user access, and system settings
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
