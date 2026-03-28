import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { CaseDistribution } from '@/components/dashboard/CaseDistribution';
import { CaseTimeline } from '@/components/dashboard/CaseTimeline';
import { ComplianceScore } from '@/components/dashboard/ComplianceScore';
import { LawyerWorkload } from '@/components/dashboard/LawyerWorkload';
import { RealtimeAlerts } from '@/components/dashboard/RealtimeAlerts';
import { TokenUsage } from '@/components/dashboard/TokenUsage';
import { PageContainer } from '@/components/ui/PageContainer';
import { spacing } from '@/lib/design-tokens';

export default function Dashboard() {
  return (
    <PageContainer title="智能中台" description="AI 法务运营概览">
      {/* 统计卡片 */}
      <DashboardHeader />

      {/* 主内容网格：1列(mobile) → 2列(tablet) → 3列(desktop) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5 lg:gap-6">
        {/* 左侧：跨 2 列 */}
        <div className={`lg:col-span-2 ${spacing.section}`}>
          <CaseDistribution />
          <CaseTimeline />
        </div>

        {/* 右侧 */}
        <div className={spacing.section}>
          <ComplianceScore />
          <TokenUsage />
          <RealtimeAlerts />
        </div>
      </div>

      {/* 底部全宽区域 */}
      <LawyerWorkload />
    </PageContainer>
  );
}
