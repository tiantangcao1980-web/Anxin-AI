import { useState } from 'react';
import { icons } from '@/lib/icons';
import { motion } from 'framer-motion';
import { Annotation } from './AIAssistant';

interface DocumentEditorProps {
  content: string;
  onContentChange: (content: string) => void;
  onAnnotationClick: (annotation: Annotation) => void;
}

const demoDocument = `律师函

致：XX贸易有限公司

我方代表YY科技有限公司，就贵司与我委托人之间的服务协议履行问题，特致此函。

一、基本事实
2023年1月1日，双方签订《技术服务协议》，约定由我委托人为贵司提供软件开发服务，服务费用为人民币100万元。

二、违约事实
截至目前，贵司仍拖欠服务费用30万元未支付，已严重违反合同约定。

三、法律依据及主张
根据《中华人民共和国民法典》第509条规定，当事人应当按照约定全面履行自己的义务。贵司的行为已构成违约。

我方要求贵司于收到本函后7日内支付全部欠款，否则我方将通过法律途径解决。

特此函告。

XX律师事务所
2024年1月18日`;

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
];

export function DocumentEditor({ content, onContentChange, onAnnotationClick }: DocumentEditorProps) {
  const [isReviewing, setIsReviewing] = useState(false);
  const [showAnnotations, setShowAnnotations] = useState(false);

  const handleReview = () => {
    setIsReviewing(true);
    setTimeout(() => {
      setIsReviewing(false);
      setShowAnnotations(true);
    }, 2000);
  };

  const lines = demoDocument.split('\n');

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Toolbar */}
      <div className="border-b border-border px-6 py-4 bg-background">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <icons.FileText className="w-5 h-5 text-muted-foreground" />
            <div>
              <h3 className="font-semibold text-foreground">文书编辑器</h3>
              <p className="text-xs text-muted-foreground">律师函草稿 - 正在编辑</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {showAnnotations && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 rounded-xl border border-amber-500">
                <icons.AlertCircle className="w-4 h-4 text-amber-500" />
                <span className="text-sm text-amber-500 font-medium">发现 {annotations.length} 个问题</span>
              </div>
            )}
            <button
              onClick={handleReview}
              disabled={isReviewing}
              className="px-4 py-2 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2 text-sm font-medium shadow-sm active:scale-95"
            >
              <icons.Send className="w-4 h-4" />
              {isReviewing ? '审核中...' : '提交 AI 审核'}
            </button>
          </div>
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 overflow-y-auto p-6 bg-muted">
        <div className="max-w-4xl mx-auto">
          <div className="bg-background border border-border rounded-2xl overflow-hidden shadow-sm">
            <div className="flex">
              {/* Line Numbers */}
              <div className="bg-muted px-3 py-4 border-r border-border select-none">
                {lines.map((_, index) => (
                  <div
                    key={index}
                    className="text-xs text-muted-foreground leading-relaxed h-6 flex items-center justify-end"
                  >
                    {index + 1}
                  </div>
                ))}
              </div>

              {/* Content */}
              <div className="flex-1 px-6 py-4 relative">
                {lines.map((line, index) => {
                  const lineAnnotations = showAnnotations
                    ? annotations.filter((a) => a.lineNumber === index + 1)
                    : [];

                  return (
                    <div key={index} className="relative leading-relaxed h-6 flex items-center">
                      <span className="text-foreground whitespace-pre">{line || ' '}</span>
                      {lineAnnotations.map((annotation) => (
                        <motion.button
                          key={annotation.id}
                          initial={{ scale: 0, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          onClick={() => onAnnotationClick(annotation)}
                          className={`ml-2 w-5 h-5 rounded-full flex items-center justify-center cursor-pointer hover:scale-110 transition-transform ${
                            annotation.type === 'error'
                              ? 'bg-red-500 text-white'
                              : annotation.type === 'warning'
                              ? 'bg-amber-500 text-white'
                              : annotation.type === 'suggestion'
                              ? 'bg-primary text-white'
                              : 'bg-violet-500 text-white'
                          }`}
                          title={annotation.message}
                        >
                          <span className="text-xs">!</span>
                        </motion.button>
                      ))}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Status Bar */}
      <div className="border-t border-border px-6 py-2 bg-background flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-4">
          <span>{lines.length} 行</span>
          <span>{demoDocument.length} 字符</span>
        </div>
        {showAnnotations && (
          <div className="flex items-center gap-2">
            <icons.CheckCircle className="w-3 h-3 text-emerald-600" />
            <span className="text-emerald-600">AI 审核完成</span>
          </div>
        )}
      </div>
    </div>
  );
}
