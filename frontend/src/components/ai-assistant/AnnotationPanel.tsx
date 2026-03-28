import { motion, AnimatePresence } from 'framer-motion';
import { Annotation } from './AIAssistant';
import { icons } from '@/lib/icons';

interface AnnotationPanelProps {
  selectedAnnotation: Annotation | null;
  onClose: () => void;
}

const annotations: Annotation[] = [
  {
    id: '1',
    lineNumber: 3,
    type: 'warning',
    message: '收件人信息不完整',
    detail: '建议补充收件人的详细地址、法定代表人姓名等信息，以便送达和证据固定。',
  },
  {
    id: '2',
    lineNumber: 7,
    type: 'suggestion',
    message: '建议补充合同编号',
    reference: '《律师函写作规范》第8条',
    detail: '在描述合同时应注明合同编号，便于对方核查，增强说服力。',
  },
  {
    id: '3',
    lineNumber: 11,
    type: 'error',
    message: '违约事实描述不够详细',
    reference: '《民事诉讼证据规则》',
    detail: '应列明具体的付款节点、已支付金额、欠款金额及计算依据。缺少这些细节可能影响后续诉讼中的举证。',
  },
  {
    id: '4',
    lineNumber: 14,
    type: 'learn',
    message: '法律引用规范',
    reference: '《民法典》第509条',
    detail: '引用法律条文时应完整表述。建议改为："根据《中华人民共和国民法典》第五百零九条规定..."',
  },
  {
    id: '5',
    lineNumber: 16,
    type: 'warning',
    message: '缺少违约金条款提醒',
    detail: '如合同中约定了违约金或逾期利息，应在此处明确主张，否则可能被视为放弃该权利。',
  },
];

export function AnnotationPanel({ selectedAnnotation, onClose }: AnnotationPanelProps) {
  const typeConfig = {
    error: {
      icon: icons.AlertCircle,
      color: 'text-destructive',
      bg: 'bg-destructive/5',
      border: 'border-destructive',
      label: '错误',
    },
    warning: {
      icon: icons.AlertTriangle,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
      border: 'border-amber-500',
      label: '警告',
    },
    suggestion: {
      icon: icons.Lightbulb,
      color: 'text-primary',
      bg: 'bg-primary/5',
      border: 'border-primary',
      label: '建议',
    },
    learn: {
      icon: icons.BookOpen,
      color: 'text-violet-500',
      bg: 'bg-violet-50',
      border: 'border-violet-500',
      label: '学习',
    },
  };

  return (
    <div className="h-full bg-background">
      <div className="p-4 lg:p-6">
        <div className="flex items-center justify-between mb-4 lg:mb-6">
          <h3 className="font-semibold text-foreground">AI 批注建议</h3>
          <span className="text-sm text-muted-foreground">{annotations.length} 条建议</span>
        </div>

        <AnimatePresence mode="wait">
          {selectedAnnotation ? (
            <motion.div
              key="detail"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-3 lg:space-y-4"
            >
              {/* Detail View */}
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  {(() => {
                    const config = typeConfig[selectedAnnotation.type];
                    const Icon = config.icon;
                    return (
                      <>
                        <div className={`w-10 h-10 rounded-xl ${config.bg} flex items-center justify-center flex-shrink-0`}>
                          <Icon className={`w-5 h-5 ${config.color}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <span className={`text-xs font-medium ${config.color}`}>
                            {config.label} · 第 {selectedAnnotation.lineNumber} 行
                          </span>
                          <h4 className="font-medium text-foreground mt-1">
                            {selectedAnnotation.message}
                          </h4>
                        </div>
                      </>
                    );
                  })()}
                </div>
                <button
                  onClick={onClose}
                  className="p-1 hover:bg-muted rounded-lg transition-colors flex-shrink-0"
                >
                  <icons.X className="w-4 h-4 text-muted-foreground" />
                </button>
              </div>

              <div className="bg-muted rounded-xl p-4 border border-border">
                <p className="text-sm text-foreground/80 leading-relaxed">
                  {selectedAnnotation.detail}
                </p>
              </div>

              {selectedAnnotation.reference && (
                <div className="bg-primary/5 rounded-xl p-4 border border-primary/20">
                  <div className="flex items-center gap-2 mb-2">
                    <icons.BookOpen className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium text-primary">法律依据</span>
                  </div>
                  <p className="text-sm text-foreground">{selectedAnnotation.reference}</p>
                </div>
              )}

              <div className="flex items-center gap-2 pt-4 border-t border-border">
                <button className="flex-1 py-2.5 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors text-sm font-medium active:scale-98 shadow-sm">
                  采纳建议
                </button>
                <button className="px-4 py-2.5 border border-border text-foreground rounded-xl hover:bg-muted transition-colors text-sm font-medium active:scale-98">
                  忽略
                </button>
              </div>

              <div className="flex items-center justify-center gap-4 pt-2">
                <button className="flex items-center gap-1 text-xs text-muted-foreground hover:text-emerald-600 transition-colors active:scale-95">
                  <icons.ThumbsUp className="w-3 h-3" />
                  <span>有帮助</span>
                </button>
                <button className="flex items-center gap-1 text-xs text-muted-foreground hover:text-destructive transition-colors active:scale-95">
                  <icons.ThumbsDown className="w-3 h-3" />
                  <span>无帮助</span>
                </button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="list"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-2 lg:space-y-3"
            >
              {/* List View */}
              {annotations.map((annotation, index) => {
                const config = typeConfig[annotation.type];
                const Icon = config.icon;

                return (
                  <motion.button
                    key={annotation.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => {}}
                    className={`w-full text-left p-3 lg:p-4 rounded-xl border ${config.bg} ${config.border} hover:shadow-md transition-all active:scale-[0.99]`}
                  >
                    <div className="flex items-start gap-3">
                      <Icon className={`w-4 h-4 ${config.color} flex-shrink-0 mt-0.5`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className={`text-xs font-medium ${config.color}`}>
                            {config.label}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            第 {annotation.lineNumber} 行
                          </span>
                        </div>
                        <p className="text-sm text-foreground leading-relaxed line-clamp-2">
                          {annotation.message}
                        </p>
                      </div>
                    </div>
                  </motion.button>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
