import { useState } from 'react';
import { createPortal } from 'react-dom';
import { icons } from '@/lib/icons';
import { usePrivacy, PrivacyMode, HardwareStatus as HWStatus } from '../../context/PrivacyContext';
import { buttonStyle } from '@/lib/design-tokens';
import { toast } from 'sonner';

const OPENCLAW_SETUP_GUIDE = [
  '1. 确认本机满足最低硬件要求（建议 8GB 内存、20GB 可用磁盘）。',
  '2. 拉取 OpenClaw 运行时与法律模型包。',
  '3. 配置本地推理服务地址、模型目录和隐私策略。',
  '4. 完成本地联调后，再回到平台点击“我已完成部署”。',
].join('\n');

/**
 * HardwareStatus - AI 私有助手状态组件
 *
 * 作为 OpenClaw 管理入口：
 * - 本地模式（L1/L2）：引导安装 OpenClaw 本地部署
 * - 云端模式（L3）：提示云端私有助手功能开发中
 * - 已安装时显示连接状态和算力使用
 */
export const HardwareStatus = () => {
  const {
    mode,
    hardwareStatus,
    hardwareName,
    secureComputeUsage,
    openClawInstalled,
    toggleHardwareConnection,
    setOpenClawInstalled,
  } = usePrivacy();

  const [showSetupGuide, setShowSetupGuide] = useState(false);
  const isConnected = hardwareStatus === HWStatus.CONNECTED;
  const isCloudMode = mode === PrivacyMode.CLOUD;

  const handleClick = () => {
    if (!openClawInstalled) {
      setShowSetupGuide(true);
    } else {
      toggleHardwareConnection();
    }
  };

  const handleCompleteSetup = () => {
    setOpenClawInstalled(true);
    setShowSetupGuide(false);
    toggleHardwareConnection();
  };

  /** 顶栏仅图标：完整状态写入 title / aria-label */
  const statusTitle = !openClawInstalled
    ? 'AI 私有助手 · 点击配置'
    : isConnected
      ? `${hardwareName} · 已连接 · 算力 ${Math.round(secureComputeUsage)}%`
      : 'AI 私有助手（离线）· 点击连接';

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        title={statusTitle}
        aria-label={statusTitle}
        className={`relative shrink-0 flex items-center justify-center p-2 rounded-lg border transition-all ${
          isConnected
            ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-950/50'
            : !openClawInstalled
              ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-950/50'
              : 'bg-muted border-border text-muted-foreground hover:bg-muted/80'
        }`}
      >
        <icons.Cpu className="w-4 h-4" />
        {isConnected ? (
          <span
            className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-emerald-500 ring-2 ring-background"
            aria-hidden
          />
        ) : !openClawInstalled ? (
          <span
            className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-amber-500 ring-2 ring-background"
            aria-hidden
          />
        ) : null}
      </button>

      {/* 使用 Portal 渲染弹窗到 body，避免被父元素 overflow 裁剪 */}
      {showSetupGuide && createPortal(
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={(e) => { if (e.target === e.currentTarget) setShowSetupGuide(false); }}
        >
          <div className="bg-background rounded-2xl shadow-2xl border border-border w-full max-w-lg mx-4 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="bg-gradient-to-r from-primary/10 to-primary/5 px-6 py-5 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-xl">
                    <icons.Cpu className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-foreground">AI 私有助手</h3>
                    <p className="text-sm text-muted-foreground">
                      {isCloudMode ? '云端私有助手服务' : '基于 OpenClaw 的本地私有化 AI 服务'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowSetupGuide(false)}
                  className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  <icons.X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Content — 根据模式区分 */}
            <div className="px-6 py-5 space-y-4">
              {isCloudMode ? (
                /* ===== 云端模式：功能开发中 ===== */
                <div className="text-center py-6 space-y-4">
                  <div className="mx-auto w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center">
                    <icons.Cloud className="w-8 h-8 text-primary" />
                  </div>
                  <div>
                    <h4 className="text-base font-semibold text-foreground mb-1">云端私有助手</h4>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      云端私有助手仍处于规划与预研阶段。后续开放后，将为您提供专属的云端 AI 法务服务实例、
                      数据隔离存储与独享算力资源。
                    </p>
                  </div>
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 rounded-full text-xs font-medium border border-amber-200 dark:border-amber-800">
                    <icons.Clock className="w-3.5 h-3.5" />
                    当前尚未开放申请
                  </div>
                </div>
              ) : (
                /* ===== 本地模式：OpenClaw 安装引导 ===== */
                <>
                  <p className="text-sm text-muted-foreground">
                    AI 私有助手基于 OpenClaw 开源框架，支持本地部署、数据完全自主可控。请按以下步骤完成安装：
                  </p>
                  <div className="space-y-3">
                    {[
                      { step: 1, title: '环境检测', desc: '检查系统是否满足最低硬件要求（8GB RAM、20GB 磁盘空间）' },
                      { step: 2, title: '下载 OpenClaw', desc: '从官方仓库拉取 OpenClaw 运行时和法律领域模型包' },
                      { step: 3, title: '配置服务', desc: '设置本地推理引擎、隐私策略和数据存储路径' },
                      { step: 4, title: '验证连接', desc: '启动本地服务并验证与安心法务平台的通信' },
                    ].map((item) => (
                      <div key={item.step} className="flex gap-3">
                        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">
                          {item.step}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-foreground">{item.title}</p>
                          <p className="text-xs text-muted-foreground">{item.desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-border flex justify-end gap-3">
              <button
                onClick={() => setShowSetupGuide(false)}
                className={`${buttonStyle.sm} px-4 py-2 text-muted-foreground hover:bg-muted`}
              >
                {isCloudMode ? '知道了' : '稍后安装'}
              </button>
              {isCloudMode && (
                <button
                  onClick={() => { window.location.href = '/pricing' }}
                  className={`${buttonStyle.sm} px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm`}
                >
                  查看企业方案
                </button>
              )}
              {!isCloudMode && (
                <>
                  <button
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(OPENCLAW_SETUP_GUIDE);
                        toast.success('安装说明已复制');
                      } catch {
                        toast.info('请根据弹窗步骤手动完成部署');
                      }
                    }}
                    className={`${buttonStyle.sm} px-4 py-2 text-muted-foreground hover:bg-muted`}
                  >
                    复制安装说明
                  </button>
                  <button
                    onClick={handleCompleteSetup}
                    className={`${buttonStyle.sm} px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm`}
                  >
                    我已完成部署
                  </button>
                </>
              )}
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
};
