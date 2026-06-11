import { useAuth } from "@/context/AuthContext";
import { WelcomeContent } from "./DashboardPage";

export function DashboardHome() {
  const { user } = useAuth();
  if (!user) return null;

  return <WelcomeContent role={user.role} />;
}
