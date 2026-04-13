import { QuickActionsBar, type QuickActionFillPayload } from './QuickActionsBar';
import { KnowledgeBaseSelector } from './KnowledgeBaseSelector';

interface InputOrchestrationBarProps {
  onFillInput: (payload: QuickActionFillPayload) => void;
  isProcessing: boolean;
  isMobile: boolean;
  activeActionId?: string | null;
  attachmentName?: string | null;
  selectedKbIds: string[];
  selectedTemplateId: string | null;
  onKnowledgeSelectionChange: (ids: string[]) => void;
  onTemplateSelectionChange: (id: string | null) => void;
}

export function InputOrchestrationBar({
  onFillInput,
  isProcessing,
  isMobile,
  activeActionId = null,
  attachmentName = null,
  selectedKbIds,
  selectedTemplateId,
  onKnowledgeSelectionChange,
  onTemplateSelectionChange,
}: InputOrchestrationBarProps) {
  return (
    <div
      data-testid="input-orchestration-bar"
      className="mb-2 flex items-center gap-1.5 overflow-hidden rounded-2xl bg-background px-2.5 py-2"
    >
      <KnowledgeBaseSelector
        selectedKbIds={selectedKbIds}
        selectedTemplateId={selectedTemplateId}
        onKnowledgeSelectionChange={onKnowledgeSelectionChange}
        onTemplateSelectionChange={onTemplateSelectionChange}
        disabled={isProcessing}
        embedded
      />
      <QuickActionsBar
        onFillInput={onFillInput}
        isProcessing={isProcessing}
        isMobile={isMobile}
        activeActionId={activeActionId}
        attachmentName={attachmentName}
        className="min-w-0 flex-1 overflow-hidden"
      />
    </div>
  );
}
