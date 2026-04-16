import { useState, useRef } from 'react';
import { icons } from '@/lib/icons';
import { motion } from 'framer-motion';

interface MultiModalInputProps {
  onSend: (content: string, file?: File) => void;
  disabled?: boolean;
}

export function MultiModalInput({ onSend, disabled }: MultiModalInputProps) {
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() || fileInputRef.current?.files?.[0]) {
      onSend(input.trim(), fileInputRef.current?.files?.[0]);
      setInput('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onSend('', file);
      e.target.value = '';
    }
  };

  return (
    <div className="border-t border-border p-4 bg-background">
      <form onSubmit={handleSubmit} className="flex items-end gap-3 max-w-4xl mx-auto">
        {/* File Upload */}
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileChange}
          className="hidden"
          accept=".pdf,.doc,.docx,.txt,.md,.xlsx,.xls,.csv,.pptx,image/*"
        />
        
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="p-2.5 rounded-lg hover:bg-primary-50 text-muted-foreground hover:text-primary transition-[colors,transform] active:scale-95 outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
        >
          <icons.Paperclip className="w-5 h-5" />
        </button>

        {/* Text Input */}
        <div className="flex-1 relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder="输入您的法律问题，或上传合同文件..."
            disabled={disabled}
            rows={1}
            className="w-full px-4 py-3 bg-muted border-none rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary/10 focus:bg-background transition-colors disabled:opacity-50 text-foreground placeholder:text-muted-foreground text-sm"
            style={{ minHeight: '48px', maxHeight: '120px' }}
          />
        </div>

        {/* Voice & Camera */}
        <motion.button
          type="button"
          onClick={() => setIsRecording(!isRecording)}
          disabled={disabled}
          whileTap={{ scale: 0.95 }}
          className={`p-2.5 rounded-lg transition-colors disabled:opacity-50 ${
            isRecording
              ? 'bg-destructive text-destructive-foreground'
              : 'hover:bg-primary-50 text-muted-foreground hover:text-primary'
          }`}
        >
          <icons.Mic className="w-5 h-5" />
        </motion.button>

        <button
          type="button"
          disabled={disabled}
          className="p-2.5 rounded-lg hover:bg-primary-50 text-muted-foreground hover:text-primary transition-[colors,transform] active:scale-95 outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
        >
          <icons.Camera className="w-5 h-5" />
        </button>

        {/* Send Button */}
        <motion.button
          type="submit"
          disabled={disabled || (!input.trim() && !fileInputRef.current?.files?.[0])}
          whileTap={{ scale: 0.95 }}
          className="p-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary-600 shadow-legal-sm transition-[colors,transform] disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-1"
        >
          <icons.Send className="w-5 h-5" />
        </motion.button>
      </form>

      <div className="mt-3 flex items-center justify-center gap-2 text-[10px] text-muted-foreground font-medium uppercase tracking-caption">
        <div className="w-1.5 h-1.5 bg-success rounded-full animate-pulse"></div>
        <span>安心AI法务：支持文本 / 语音 / 图片 / 文件多模态输入</span>
      </div>
    </div>
  );
}
