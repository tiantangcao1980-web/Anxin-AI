/**
 * 智能体工作台 v2 — 多 Agent 并列协作 + 交互式面板
 * 
 * 功能区域（自上而下）：
 * 1. 需求分析卡片 — 来自需求分析 Agent
 * 2. 需求确认交互卡片 — 单选/多选，由左侧对话触发
 * 3. Agent 协作看板 — 多 Agent 卡片式并列展示运行状态与进度
 * 4. Agent 执行结果时间线 — 已完成任务的结果
 * 5. 动作按钮区 — 系统或 Agent 推送的快捷操作
 * 6. A2UI 动态组件 — 由 Agent 推送的自定义 UI
 */

import { memo, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { iconSize, heading, statusColor, radius } from '@/lib/design-tokens';
import { RequirementCard } from './RequirementCard';
import { AgentCard } from './AgentCard';
import { AgentTaskBoard } from './AgentTaskBoard';
import { WorkspaceConfirmationCard } from './WorkspaceConfirmationCard';
import { WorkspaceActionBar } from './WorkspaceActionBar';
import { A2UIRenderer } from './LegacyA2UIRenderer';
import { ContractReviewCard } from './ContractReviewCard';
import { useChatStore } from '@/lib/store';
import type { AgentResult, ThinkingStep, RequirementAnalysis } from '@/lib/store';

interface AgentWorkspaceProps {
  agentResults: AgentResult[];
  thinkingSteps: ThinkingStep[];
  requirementAnalysis: RequirementAnalysis | null;
  a2uiData: any;
  isProcessing: boolean;
  onWorkspaceConfirm?: (confirmationId: string, selectedIds: string[]) => void;
  onWorkspaceAction?: (actionId: string, payload?: any) => void;
}

export const AgentWorkspace = memo(function AgentWorkspace({
  agentResults,
  thinkingSteps,
  requirementAnalysis,
  a2uiData,
  isProcessing,
  onWorkspaceConfirm,
  onWorkspaceAction,
}: AgentWorkspaceProps) {
  const store = useChatStore();
  const { workspaceConfirmations, workspaceActions, agentTasks } = store;

  // 判断是否有内容
  const hasConfirmations = workspaceConfirmations.length > 0;
  const hasActions = workspaceActions.length > 0;
  const hasTasks = agentTasks.length > 0;
  const isEmpty = !requirementAnalysis && agentResults.length === 0 && !a2uiData
    && !hasConfirmations && !hasActions && !hasTasks;

  // 按状态分组 agent 结果
  const completedResults = useMemo(() => agentResults, [agentResults]);

  // 合同审查卡片可见性（由上传合同文件触发）
  const contractReviewVisible = store.contractReviewVisible;

  if (isEmpty && !isProcessing && !contractReviewVisible) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4 px-8">
          <div className="w-16 h-16 mx-auto bg-primary/10 rounded-2xl flex items-center justify-center shadow-sm">
            <icons.LayoutDashboard className={`${iconSize.xl} text-primary`} />
          </div>
          <div>
            <h3 className="font-semibold text-foreground mb-1.5">智能工作台</h3>
            <p className={`${heading.micro} leading-relaxed`}>
              发送消息后，此区域将实时展示<br />
              需求分析、Agent 协作进度和处理结果
            </p>
          </div>
          <div className="pt-2 flex flex-wrap gap-1.5 justify-center">
            {['需求确认', '多Agent协作', '进度追踪', '智能交互'].map(tag => (
              <span key={tag} className={`px-2.5 py-1 bg-background ${radius.button} text-[11px] text-muted-foreground border border-border shadow-xs`}>
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // 空闲但有合同审查卡片弹出
  if (isEmpty && !isProcessing && contractReviewVisible) {
    return (
      <div className="h-full overflow-y-auto">
        <div className="p-4 space-y-4">
          <ContractReviewCard />
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-4 space-y-4">
        {/* ===== 1. 需求分析卡片 ===== */}
        <AnimatePresence>
          {requirementAnalysis && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <RequirementCard analysis={requirementAnalysis} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ===== 2. 需求确认交互卡片 ===== */}
        <AnimatePresence>
          {workspaceConfirmations.map((confirmation) => (
            <motion.div
              key={confirmation.id}
              initial={{ opacity: 0, y: -10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.98 }}
              transition={{ duration: 0.25 }}
            >
              <WorkspaceConfirmationCard
                confirmation={confirmation}
                onConfirm={(selectedIds) => {
                  store.updateConfirmationSelection(confirmation.id, selectedIds);
                  store.confirmWorkspaceSelection(confirmation.id);
                  onWorkspaceConfirm?.(confirmation.id, selectedIds);
                }}
              />
            </motion.div>
          ))}
        </AnimatePresence>

        {/* ===== 3. Agent 协作看板（卡片式并列） ===== */}
        <AnimatePresence>
          {hasTasks && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <AgentTaskBoard tasks={agentTasks} isProcessing={isProcessing} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ===== 4. Agent 执行结果时间线 ===== */}
        {completedResults.length > 0 && (
          <div className="space-y-0">
            <div className="flex items-center gap-2 mb-3 px-1">
              <icons.Zap className="w-3.5 h-3.5 text-primary" />
              <span className={`${heading.micro} font-bold`}>执行结果</span>
              <span className={`text-[10px] px-2 py-0.5 ${statusColor.info} ${radius.avatar} font-medium`}>
                {completedResults.length}
              </span>
            </div>
            {completedResults.map((result, index) => (
              <AgentCard
                key={result.id}
                result={result}
                index={index}
                isLast={index === completedResults.length - 1 && !isProcessing}
              />
            ))}
          </div>
        )}

        {/* ===== 5. 动作按钮区 ===== */}
        <AnimatePresence>
          {hasActions && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <WorkspaceActionBar
                actions={workspaceActions}
                onAction={(actionId, payload) => {
                  onWorkspaceAction?.(actionId, payload);
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ===== 6. 正在处理指示（仅在无任务看板且无结果时显示） ===== */}
        <AnimatePresence>
          {isProcessing && !hasTasks && agentResults.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center justify-center gap-2 py-4"
            >
              <icons.Loader2 className={`${iconSize.sm} animate-spin text-primary`} />
              <span className="text-sm text-primary font-medium">智能体正在处理中...</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ===== 6.5 思考链/推理过程展示（工作台内） ===== */}
        {thinkingSteps.length > 0 && (
          <div className="space-y-0">
            <div className="flex items-center gap-2 mb-3 px-1">
              <icons.Loader2 className={`w-3.5 h-3.5 ${isProcessing ? 'animate-spin text-primary' : 'text-muted-foreground'}`} />
              <span className={`${heading.micro} font-bold`}>推理过程</span>
              <span className={`text-[10px] px-2 py-0.5 ${statusColor.info} ${radius.avatar} font-medium`}>
                {thinkingSteps.length} 步
              </span>
            </div>
            <div className="ml-2 pl-3 border-l-2 border-dashed border-border space-y-2">
              {thinkingSteps.map((step, idx) => (
                <motion.div
                  key={step.id}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="text-xs"
                >
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="font-semibold text-foreground">{step.agent || '分析'}</span>
                    <span className={`px-1.5 py-0.5 ${radius.avatar} text-[10px] font-medium ${
                      step.phase === 'planning' ? statusColor.info :
                      step.phase === 'requirement' ? statusColor.warning :
                      step.phase === 'result' ? statusColor.success :
                      statusColor.info
                    }`}>
                      {step.phase === 'planning' ? 'DAG规划' :
                       step.phase === 'requirement' ? '需求分析' :
                       step.phase === 'result' ? '完成' : '推理'}
                    </span>
                  </div>
                  <p className="text-muted-foreground leading-relaxed line-clamp-3">{step.content}</p>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* ===== 7. 处理中指示（有内容但仍在处理时，底部显示小型指示） ===== */}
        {isProcessing && (hasTasks || agentResults.length > 0 || thinkingSteps.length > 0) && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-1.5 py-2 px-1"
          >
            <icons.Loader2 className={`${iconSize.xs} animate-spin text-primary`} />
            <span className="text-[11px] text-primary font-medium">继续处理中...</span>
          </motion.div>
        )}

        {/* ===== 8. A2UI 动态组件区域 ===== */}
        {a2uiData && (
          <div className="mt-2 pt-3 border-t border-border">
            <A2UIRenderer data={a2uiData} />
          </div>
        )}

        {/* ===== 9. 合同审查卡片（仅上传合同时弹出） ===== */}
        <AnimatePresence>
          {contractReviewVisible && (
            <motion.div
              initial={{ opacity: 0, y: 15, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 15, scale: 0.97 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              className="mt-3 pt-3 border-t border-border"
            >
              <ContractReviewCard />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
});
