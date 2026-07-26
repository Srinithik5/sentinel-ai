import {
  AttackDistributionChart,
  GeoDistributionChart,
  HourlyActivityChart,
  RiskDistributionChart,
  SeverityDistributionChart,
  TopResourcesChart,
} from "@/components/analytics/Charts";
import { PageHeader } from "@/components/ui/PageHeader";

export default function AnalyticsPage() {
  return (
    <>
      <PageHeader
        title="Analytics"
        description="Trends and behavioral patterns derived from the detection, classification, and explainability pipelines."
      />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <AttackDistributionChart />
        <SeverityDistributionChart />
        <RiskDistributionChart />
        <HourlyActivityChart />
        <TopResourcesChart />
        <GeoDistributionChart />
      </div>
    </>
  );
}