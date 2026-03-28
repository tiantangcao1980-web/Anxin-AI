/**
 * FirmManagement - 律所内部管理主页面
 *
 * 包含三个 Tab:
 * 1. 团队管理 (TeamManagement)
 * 2. 工时管理 (TimesheetTable)
 * 3. 收入报表 (RevenueReport)
 */

import { PageContainer } from '@/components/ui/PageContainer'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { icons } from '@/lib/icons'
import { iconSize } from '@/lib/design-tokens'
import TeamManagement from '@/components/firm/TeamManagement'
import TimesheetTable from '@/components/firm/TimesheetTable'
import RevenueReport from '@/components/firm/RevenueReport'

export default function FirmManagement() {
  return (
    <PageContainer
      title="律所管理"
      description="团队、工时与收入一站式管理"
      scrollable={false}
    >
      <Tabs defaultValue="teams" className="flex-1 flex flex-col min-h-0">
        <TabsList className="shrink-0">
          <TabsTrigger value="teams" className="gap-1.5">
            <icons.Users className={iconSize.sm} />
            团队管理
          </TabsTrigger>
          <TabsTrigger value="timesheet" className="gap-1.5">
            <icons.Clock className={iconSize.sm} />
            工时管理
          </TabsTrigger>
          <TabsTrigger value="revenue" className="gap-1.5">
            <icons.BarChart3 className={iconSize.sm} />
            收入报表
          </TabsTrigger>
        </TabsList>

        <TabsContent value="teams" className="flex-1 min-h-0 mt-4">
          <TeamManagement />
        </TabsContent>

        <TabsContent value="timesheet" className="flex-1 min-h-0 mt-4">
          <TimesheetTable />
        </TabsContent>

        <TabsContent value="revenue" className="flex-1 min-h-0 mt-4">
          <RevenueReport />
        </TabsContent>
      </Tabs>
    </PageContainer>
  )
}
