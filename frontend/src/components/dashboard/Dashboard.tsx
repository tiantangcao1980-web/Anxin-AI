import { DashboardHeader } from './DashboardHeader';
import { CaseDistribution } from './CaseDistribution';
import { LawyerWorkload } from './LawyerWorkload';
import { ComplianceScore } from './ComplianceScore';
import { TokenUsage } from './TokenUsage';
import { RealtimeAlerts } from './RealtimeAlerts';
import { CaseTimeline } from './CaseTimeline';

export function Dashboard() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-7xl mx-auto p-4 lg:p-6 space-y-4 lg:space-y-6">
        {/* Header Stats */}
        <DashboardHeader />

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-4 lg:space-y-6">
            <CaseDistribution />
            <LawyerWorkload />
            <div className="lg:hidden">
              <ComplianceScore />
            </div>
            <CaseTimeline />
          </div>

          {/* Right Column */}
          <div className="space-y-4 lg:space-y-6">
            <div className="hidden lg:block">
              <ComplianceScore />
            </div>
            <TokenUsage />
            <RealtimeAlerts />
          </div>
        </div>
      </div>
    </div>
  );
}