import { useMemo, useState } from 'react'
import { documentsApi } from '@/lib/api'
import { cardStyle } from '@/lib/design-tokens'
import { useCollaborationSession } from './hooks/useCollaborationSession'
import { useDocumentWorkbenchStore } from './hooks/useDocumentWorkbenchStore'

interface WorkbenchRightPanelProps {
  entryMode: 'library' | 'collaboration' | 'chat'
  sessionId?: string | null
}

type WorkbenchPanelTab = 'collaboration' | 'ai' | 'history' | 'properties'

export function WorkbenchRightPanel({ entryMode, sessionId }: WorkbenchRightPanelProps) {
  const { defaultTab, session, collaborators, versions, activityItems, restoringSnapshotId, restoreVersion } = useCollaborationSession(entryMode, sessionId)
  const [activeTab, setActiveTab] = useState<WorkbenchPanelTab>(defaultTab as WorkbenchPanelTab)
  const [generatingKey, setGeneratingKey] = useState<string | null>(null)
  const { openTabs, activeDocumentId, updateDocumentContent, markMissingFieldHandled } = useDocumentWorkbenchStore()
  const activeDocument = openTabs.find((item) => item.id === activeDocumentId)
  const metadata = activeDocument?.metadata
  const missingFields = metadata?.missing_fields ?? []
  const handledMissingFields = metadata?.handled_missing_fields ?? []
  const pendingMissingFields = useMemo(
    () => missingFields.filter((item) => !item.handled),
    [missingFields],
  )
  const hasAIMetadata = Boolean(metadata?.draft_mode || pendingMissingFields.length > 0)
  const historyItems = useMemo(
    () => [
      ...handledMissingFields
        .slice()
        .reverse()
        .map((item) => ({
          id: `handled-${item.key}`,
          label: '已处理待确认事项',
          description: `${item.label} · ${item.action}`,
          targetText: item.action === 'AI补写' ? `## AI补写段落：${item.label}` : `## 待补充：${item.label}`,
        })),
      ...activityItems,
      {
        id: 'open-document',
        label: '打开文档',
        description: activeDocument ? `已打开 ${activeDocument.title}` : '等待打开文档',
      },
      {
        id: 'sync-status',
        label: '同步状态',
        description: session ? `会话版本 ${session.current_version}` : '已同步到本地工作台',
      },
    ],
    [activeDocument, activityItems, handledMissingFields, session],
  )
  const documentTypeLabel =
    activeDocument?.kind === 'markdown'
      ? 'Markdown'
      : activeDocument?.kind === 'pdf'
        ? 'PDF'
        : activeDocument?.kind === 'txt'
          ? 'TXT'
          : activeDocument?.kind === 'spreadsheet'
            ? '表格'
            : activeDocument?.kind === 'presentation'
              ? '演示'
          : activeDocument?.kind === 'doc'
            ? '文档'
            : '未打开'

  const handleInsertSuggestion = (item: { key: string; label: string; suggestion: string; severity: 'high' | 'medium' | 'low'; group: string }) => {
    if (!activeDocument) return
    const nextBlock = `\n\n## 待补充：${item.label}\n${item.suggestion}\n`
    const currentContent = activeDocument.content ?? ''
    if (!currentContent.includes(nextBlock.trim())) {
      updateDocumentContent(activeDocument.id, `${currentContent.trimEnd()}${nextBlock}`)
    }
    markMissingFieldHandled(activeDocument.id, item, '插入建议')
  }

  const handleGenerateParagraph = async (item: { key: string; label: string; suggestion: string; severity: 'high' | 'medium' | 'low'; group: string }) => {
    if (!activeDocument) return
    setGeneratingKey(item.key)
    try {
      const generated = await documentsApi.generateParagraph({
        doc_type: activeDocument.title,
        document_title: activeDocument.title,
        current_content: activeDocument.content ?? '',
        missing_field: item,
      })
      const nextBlock = `\n\n## ${generated.title}\n${generated.content}\n`
      const currentContent = activeDocument.content ?? ''
      if (!currentContent.includes(nextBlock.trim())) {
        updateDocumentContent(activeDocument.id, `${currentContent.trimEnd()}${nextBlock}`)
      }
      markMissingFieldHandled(activeDocument.id, item, 'AI补写')
    } catch (error) {
      const nextBlock = `\n\n## AI补写段落：${item.label}\n${item.suggestion}\n`
      const currentContent = activeDocument.content ?? ''
      if (!currentContent.includes(nextBlock.trim())) {
        updateDocumentContent(activeDocument.id, `${currentContent.trimEnd()}${nextBlock}`)
      }
      markMissingFieldHandled(activeDocument.id, item, 'AI补写')
    } finally {
      setGeneratingKey(null)
    }
  }

  const handleLocateHistoryItem = (targetText?: string) => {
    if (!activeDocument || !targetText) return
    window.dispatchEvent(
      new CustomEvent('workbench:locate-content', {
        detail: {
          documentId: activeDocument.id,
          targetText,
        },
      }),
    )
  }

  return (
    <aside className="flex w-80 flex-col border-l border-border bg-surface-1/90">
      <div className="flex items-center gap-2 border-b border-border px-3 py-3">
        <button
          type="button"
          role="tab"
          data-state={activeTab === 'collaboration' ? 'active' : 'inactive'}
          onClick={() => setActiveTab('collaboration')}
          className={`rounded-lg px-3 py-1.5 text-sm ${
            activeTab === 'collaboration' ? 'bg-primary/10 text-primary' : 'text-muted-foreground'
          }`}
        >
          协作
        </button>
        <button
          type="button"
          role="tab"
          data-state={activeTab === 'ai' ? 'active' : 'inactive'}
          onClick={() => setActiveTab('ai')}
          className={`rounded-lg px-3 py-1.5 text-sm ${
            activeTab === 'ai' ? 'bg-primary/10 text-primary' : 'text-muted-foreground'
          }`}
        >
          AI
        </button>
        <button
          type="button"
          role="tab"
          data-state={activeTab === 'history' ? 'active' : 'inactive'}
          onClick={() => setActiveTab('history')}
          className={`rounded-lg px-3 py-1.5 text-sm ${
            activeTab === 'history' ? 'bg-primary/10 text-primary' : 'text-muted-foreground'
          }`}
        >
          历史
        </button>
        <button
          type="button"
          role="tab"
          data-state={activeTab === 'properties' ? 'active' : 'inactive'}
          onClick={() => setActiveTab('properties')}
          className={`rounded-lg px-3 py-1.5 text-sm ${
            activeTab === 'properties' ? 'bg-primary/10 text-primary' : 'text-muted-foreground'
          }`}
        >
          属性
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'collaboration' ? (
          <div className="space-y-4">
            {session ? (
              <div className={`${cardStyle.compact} !px-3 !py-3`}>
                <div className="text-sm font-medium text-foreground">{session.name || '协作会话'}</div>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <span className="rounded-full bg-muted px-2.5 py-1">版本 {session.current_version}</span>
                  <span className="rounded-full bg-muted px-2.5 py-1">状态 {session.status}</span>
                  <span className="rounded-full bg-muted px-2.5 py-1">
                    在线 {session.active_collaborators}/{session.max_collaborators}
                  </span>
                  <span className="rounded-full bg-muted px-2.5 py-1">快照 {versions.length}</span>
                </div>
              </div>
            ) : null}

            <div>
            <h3 className="text-sm font-medium text-foreground">在线成员</h3>
            <div className="mt-3 space-y-2">
              {collaborators.length > 0 ? (
                collaborators.map((item) => (
                  <div key={item.id} className={`${cardStyle.compact} !px-3 !py-2`}>
                    <div className="text-sm font-medium text-foreground">{item.name}</div>
                    <div className="text-xs text-muted-foreground">{item.role}</div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-border px-3 py-6 text-sm text-muted-foreground">
                  暂无协作者
                </div>
              )}
            </div>
            </div>

            <div>
              <h3 className="text-sm font-medium text-foreground">版本历史</h3>
              <div className="mt-3 space-y-2">
                {versions.length > 0 ? (
                  versions.map((item) => (
                    <div key={item.id} className={`${cardStyle.compact} !px-3 !py-2`}>
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-sm font-medium text-foreground">{item.description || '未命名快照'}</div>
                        <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                          V{item.version}
                        </span>
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">{item.snapshot_type}</div>
                      <div className="mt-3 flex justify-end">
                        <button
                          type="button"
                          onClick={() => void restoreVersion(item)}
                          disabled={restoringSnapshotId === item.id}
                          className="rounded-lg border border-primary/20 bg-primary/5 px-2.5 py-1.5 text-xs text-primary transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {restoringSnapshotId === item.id ? '恢复中...' : `恢复 V${item.version}`}
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl border border-dashed border-border px-3 py-6 text-sm text-muted-foreground">
                    暂无版本快照
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : activeTab === 'ai' ? (
          <div>
            <h3 className="text-sm font-medium text-foreground">智能操作</h3>
            <div className="mt-3 space-y-4">
              {hasAIMetadata ? (
                <div className="space-y-3">
                  <div className={`${cardStyle.compact} !px-3 !py-3`}>
                    <div className="text-xs text-muted-foreground">生成状态</div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {metadata?.draft_mode ? (
                        <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
                          {metadata.draft_mode}
                        </span>
                      ) : null}
                      {typeof metadata?.completeness_score === 'number' ? (
                        <span className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
                          完整度 {Math.round(metadata.completeness_score * 100)}%
                        </span>
                      ) : null}
                      {typeof metadata?.validation_score === 'number' ? (
                        <span className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
                          质量 {Math.round(metadata.validation_score * 100)}%
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <div className={`${cardStyle.compact} !px-3 !py-3`}>
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-medium text-foreground">待确认事项</div>
                      <div className="text-xs text-muted-foreground">{pendingMissingFields.length} 项</div>
                    </div>
                    <div className="mt-3 space-y-2">
                      {pendingMissingFields.length > 0 ? (
                        pendingMissingFields.map((item) => (
                          <div key={item.key} className="rounded-xl border border-border/80 bg-surface-1 px-3 py-2">
                            <div className="flex items-center justify-between gap-2">
                              <div className="text-sm font-medium text-foreground">{item.label}</div>
                              <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                                {item.severity}
                              </span>
                            </div>
                            <div className="mt-1 text-xs text-muted-foreground">{item.group}</div>
                            <div className="mt-2 text-xs leading-5 text-foreground/80">{item.suggestion}</div>
                            <div className="mt-3 flex justify-end gap-2">
                              <button
                                type="button"
                                onClick={() => handleGenerateParagraph(item)}
                                disabled={generatingKey === item.key}
                                className="rounded-lg border border-primary/20 bg-primary/5 px-2.5 py-1.5 text-xs text-primary transition-colors hover:bg-primary/10"
                              >
                                {generatingKey === item.key ? '生成中...' : '生成补写段落'}
                              </button>
                              <button
                                type="button"
                                onClick={() => handleInsertSuggestion(item)}
                                className="rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs text-foreground transition-colors hover:bg-muted"
                              >
                                插入建议
                              </button>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="rounded-xl border border-dashed border-border px-3 py-5 text-sm text-muted-foreground">
                          当前文档暂无待确认事项
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : null}
              <div className="grid gap-2">
                <button type="button" className="rounded-xl border border-border bg-background px-3 py-2 text-left text-sm">
                  总结
                </button>
                <button type="button" className="rounded-xl border border-border bg-background px-3 py-2 text-left text-sm">
                  改写
                </button>
              </div>
              {!hasAIMetadata ? (
                <div className="rounded-2xl border border-dashed border-border px-3 py-5 text-sm text-muted-foreground">
                  当前文档暂无结构化 AI 生成信息
                </div>
              ) : null}
            </div>
          </div>
        ) : activeTab === 'history' ? (
          <div>
            <h3 className="text-sm font-medium text-foreground">最近活动</h3>
            <div className="mt-3 space-y-2">
              {historyItems.map((item) => (
                <div key={item.id} className={`${cardStyle.compact} !px-3 !py-3`}>
                  <div className="text-sm font-medium text-foreground">{item.label}</div>
                  {item.targetText ? (
                    <button
                      type="button"
                      onClick={() => handleLocateHistoryItem(item.targetText)}
                      className="mt-1 text-left text-xs text-primary transition-colors hover:text-primary/80"
                    >
                      {item.description}
                    </button>
                  ) : (
                    <div className="mt-1 text-xs text-muted-foreground">{item.description}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div>
            <h3 className="text-sm font-medium text-foreground">文档属性</h3>
            <div className="mt-3 space-y-2">
              <div className={`${cardStyle.compact} !px-3 !py-3`}>
                <div className="text-xs text-muted-foreground">文档标题</div>
                <div data-testid="workbench-property-title" className="mt-1 text-sm font-medium text-foreground">
                  {activeDocument?.title ?? '未打开文档'}
                </div>
              </div>
              <div className={`${cardStyle.compact} !px-3 !py-3`}>
                <div className="text-xs text-muted-foreground">文档类型</div>
                <div data-testid="workbench-property-type" className="mt-1 text-sm font-medium text-foreground">
                  {documentTypeLabel}
                </div>
              </div>
              <div className={`${cardStyle.compact} !px-3 !py-3`}>
                <div className="text-xs text-muted-foreground">协作模式</div>
                <div data-testid="workbench-property-mode" className="mt-1 text-sm font-medium text-foreground">
                  {entryMode === 'collaboration' ? '协作模板' : entryMode === 'chat' ? '智能工作台入口' : '文档工作台'}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
