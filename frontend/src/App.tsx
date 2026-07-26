import { AppShell } from "@/components/layout/AppShell";
import { TooltipProvider } from "@/components/ui/Tooltip";

export function App() {
  return (
    <TooltipProvider delayDuration={200}>
      <AppShell />
    </TooltipProvider>
  );
}