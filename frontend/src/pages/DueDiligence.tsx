import { DueDiligence as DueDiligenceComponent } from '@/components/due-diligence/DueDiligence';
import { PageContainer } from '@/components/ui/PageContainer';

export default function DueDiligence() {
  return (
    <PageContainer showHeader={false} scrollable={false} className="!p-0 !space-y-0">
      <DueDiligenceComponent />
    </PageContainer>
  );
}
