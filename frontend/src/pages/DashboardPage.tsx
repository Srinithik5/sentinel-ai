import { BackendStatusCard } from "@/components/system/BackendStatusCard";
import { PageHeader } from "@/components/ui/PageHeader";

export default function DashboardPage() {
  return (
    <>
      <PageHeader title="SentinelAI" description="AI-Powered Behavioral Anomaly Detection Platform" />
      <BackendStatusCard />
    </>
  );
}