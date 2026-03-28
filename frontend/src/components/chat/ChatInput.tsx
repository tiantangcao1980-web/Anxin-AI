/**
 * ChatInput Component
 * 负责处理用户输入
 */

import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { usePrivacy, PrivacyMode } from '@/context/PrivacyContext';
import { PendingFile } from '@/hooks';
import { cardStyle, heading, buttonStyle, iconSize, chatBubble, inputStyle } from '@/lib/design-tokens';

interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  pendingFile: PendingFile | null;
  clearPendingFile: () => void;
  sendDisabled: boolean;
  isProcessing: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement>;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onSend: () => void;
  onKeyPress: (e: React.KeyboardEvent) => void;
  onFileSelect: (file: File) => void;
}

export function ChatInput({
  input,
  setInput,
  pendingFile,
  clearPendingFile,
  sendDisabled,
  isProcessing,
  inputRef,
  fileInputRef,
  onSend,
  onKeyPress,
  onFileSelect,
}: ChatInputProps) {
  const { mode } = usePrivacy();

  // 隐私提示
  const getPrivacyHint = () => {
    switch (mode) {
      case PrivacyMode.LOCAL:
        return { text: '绝密模式：数据仅在本地处理', icon: icons.Lock, color: 'text-primary' };
      case PrivacyMode.HYBRID:
        return { text: '安全混合：敏感数据已自动脱敏', icon: icons.ShieldCheck, color: 'text-emerald-600' };
      case PrivacyMode.CLOUD:
        return { text: '云端增强：正在使用联网模型', icon: icons.Cloud, color: 'text-primary' };
    }
  };
  const privacyHint = getPrivacyHint();
  const PrivacyIcon = privacyHint.icon;

  return (
    <div className="p-3 bg-background border-t border-border">
      <div className="max-w-4xl mx-auto">
        {/* 待处理文件提示 */}
        <AnimatePresence>
          {pendingFile && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-2"
            >
              <div className={`flex items-center gap-2.5 px-3 py-2 ${cardStyle.highlight}`}>
                <div className="bg-background p-1 rounded shadow-sm">
                  <icons.FileText className={`${iconSize.sm} text-primary`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`${heading.card} truncate`}>{pendingFile.name}</p>
                  <p className={heading.micro}>{pendingFile.size}</p>
                </div>
                <button
                  onClick={clearPendingFile}
                  className={buttonStyle.icon}
                >
                  <icons.X className={iconSize.sm} />
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 输入框容器 */}
        <div className={inputStyle.chatContainer}>
          {/* 附件按钮 */}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onFileSelect(file);
              if (e.target) e.target.value = '';
            }}
            accept=".pdf,.doc,.docx,.txt,image/*"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isProcessing}
            className={`${buttonStyle.icon} disabled:opacity-50 flex-shrink-0`}
            title="上传文件"
          >
            <icons.Paperclip className={iconSize.md} />
          </button>

          {/* 文本输入 */}
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={onKeyPress}
            placeholder={pendingFile ? '描述您的需求...' : '输入法律问题，如：帮我审查这份合同...'}
            className={`${inputStyle.chatTextarea} resize-none`}
            style={{ minHeight: '40px', maxHeight: '120px' }}
            disabled={isProcessing}
            rows={1}
          />

          {/* 发送按钮 */}
          <button
            onClick={onSend}
            disabled={sendDisabled}
            className={`p-2 m-1 rounded-xl transition-all disabled:opacity-30 flex-shrink-0 ${
              input.trim()
                ? 'bg-primary text-white hover:bg-primary/90 active:scale-95 shadow-sm'
                : 'bg-transparent text-muted-foreground'
            }`}
          >
            {isProcessing ? <icons.Loader2 className={`${iconSize.sm} animate-spin`} /> : <icons.Send className={iconSize.sm} />}
          </button>
        </div>

        {/* 底部提示 */}
        <div className="flex items-center justify-center gap-3 mt-1.5">
          <div className={`flex items-center gap-1 text-[10px] font-medium ${privacyHint.color}`}>
            <PrivacyIcon className={iconSize.xs} />
            <span>{privacyHint.text}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
