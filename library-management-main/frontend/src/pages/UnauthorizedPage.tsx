// frontend/src/pages/UnauthorizedPage.tsx
// UI-SPEC Screen 5: Unauthorized (/unauthorized)
// Copywriting Contract exact match

import { useNavigate } from "react-router-dom";
import { ShieldOff } from "lucide-react";
import { Button } from "@/components/ui/button";

export function UnauthorizedPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="max-w-[400px] text-center space-y-4">
        <ShieldOff className="h-12 w-12 text-muted-foreground mx-auto" aria-hidden="true" />
        <h1 className="text-xl font-semibold text-foreground">Access denied</h1>
        <p className="text-sm text-muted-foreground">
          You don&apos;t have permission to view this page.
        </p>
        <Button
          variant="outline"
          onClick={() => navigate("/dashboard")}
        >
          Go to dashboard
        </Button>
      </div>
    </div>
  );
}
