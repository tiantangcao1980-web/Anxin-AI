/**
 * AdminFirm — 后台律所管理页面
 * 包装现有 firm 组件：团队管理、工时表、营收报表
 */
import { PageContainer } from '@/components/ui/PageContainer'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import TeamManagement from '@/components/firm/TeamManagement'
import TimesheetTable from '@/components/firm/TimesheetTable'
import RevenueReport from '@/components/firm/RevenueReport'
import { icons } from '@/lib/icons'

export default function AdminFirm() {
  return (
    <PageContainer title="律所管理" description="团队管理、工时记录和营收报表">
      <Tabs defaultValue="team">
        <TabsList>
          <TabsTrigger value="team">
            <icons.Users className="w-4 h-4 mr-1.5" />
            团队管理
          </TabsTrigger>
          <TabsTrigger value="timesheet">
            <icons.Clock className="w-4 h-4 mr-1.5" />
            工时记录
          </TabsTrigger>
          <TabsTrigger value="revenue">
            <icons.BarChart3 className="w-4 h-4 mr-1.5" />
            营收报表
          </TabsTrigger>
        </TabsList>

        <TabsContent value="team">
          <TeamManagement />
        </TabsContent>

        <TabsContent value="timesheet">
          <TimesheetTable />
        </TabsContent>

        <TabsContent value="revenue">
          <RevenueReport />
        </TabsContent>
      </Tabs>
    </PageContainer>
  )
}
