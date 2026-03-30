import { icons } from '@/lib/icons';
import { usePrivacy, PrivacyMode, HardwareStatus } from '../../context/PrivacyContext';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './dropdown-menu';

interface PrivacyToggleProps {
  /** false 时顶栏仅显示模式图标，文案见 title */
  showLabel?: boolean;
}

export const PrivacyToggle = ({ showLabel = true }: PrivacyToggleProps) => {
  const { mode, setMode, hardwareStatus } = usePrivacy();

  const isHardwareConnected = hardwareStatus === HardwareStatus.CONNECTED;

  const getModeInfo = (m: PrivacyMode) => {
    switch (m) {
      case PrivacyMode.LOCAL:
        return {
          icon: icons.Lock,
          label: '绝密模式',
          color: 'text-primary',
          bg: 'bg-primary/5',
          desc: '数据仅在本地硬件处理'
        };
      case PrivacyMode.HYBRID:
        return {
          icon: icons.ShieldCheck,
          label: '安全混合',
          color: 'text-emerald-600 dark:text-emerald-400',
          bg: 'bg-emerald-50 dark:bg-emerald-950/30',
          desc: '敏感信息自动脱敏'
        };
      case PrivacyMode.CLOUD:
        return {
          icon: icons.Cloud,
          label: '云端增强',
          color: 'text-primary',
          bg: 'bg-primary/5',
          desc: '联网获取最佳模型效果'
        };
    }
  };

  const currentInfo = getModeInfo(mode);
  const Icon = currentInfo.icon;

  const triggerTitle = `${currentInfo.label}：${currentInfo.desc}`;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          title={triggerTitle}
          aria-label={currentInfo.label}
          className={`outline-none shrink-0 flex items-center rounded-lg border transition-all ${currentInfo.bg} ${currentInfo.color} border-transparent hover:border-current/20 ${
            showLabel ? 'gap-2 px-3 py-1.5' : 'p-2 justify-center'
          }`}
        >
          <Icon className="w-4 h-4 shrink-0" />
          {showLabel && <span className="text-sm font-medium whitespace-nowrap">{currentInfo.label}</span>}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel>数据隐私保护级别</DropdownMenuLabel>
        <DropdownMenuSeparator />
        
        <DropdownMenuItem 
          onClick={() => isHardwareConnected && setMode(PrivacyMode.LOCAL)}
          disabled={!isHardwareConnected}
          className={`flex flex-col items-start gap-1 p-3 cursor-pointer ${mode === PrivacyMode.LOCAL ? 'bg-accent' : ''}`}
        >
          <div className="flex items-center gap-2 font-medium">
            <icons.Lock className="w-4 h-4 text-primary" />
            <span>绝密模式 (Local Only)</span>
            {!isHardwareConnected && <span className="text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded">需硬件</span>}
          </div>
          <span className="text-xs text-muted-foreground">物理隔绝，数据不出本地，适合处理核心机密。</span>
        </DropdownMenuItem>

        <DropdownMenuItem 
          onClick={() => setMode(PrivacyMode.HYBRID)}
          className={`flex flex-col items-start gap-1 p-3 cursor-pointer ${mode === PrivacyMode.HYBRID ? 'bg-accent' : ''}`}
        >
          <div className="flex items-center gap-2 font-medium">
            <icons.ShieldCheck className="w-4 h-4 text-emerald-500" />
            <span>安全混合 (Hybrid)</span>
          </div>
          <span className="text-xs text-muted-foreground">本地脱敏 + 云端推理，平衡安全与智能。</span>
        </DropdownMenuItem>

        <DropdownMenuItem 
          onClick={() => setMode(PrivacyMode.CLOUD)}
          className={`flex flex-col items-start gap-1 p-3 cursor-pointer ${mode === PrivacyMode.CLOUD ? 'bg-accent' : ''}`}
        >
          <div className="flex items-center gap-2 font-medium">
            <icons.Cloud className="w-4 h-4 text-primary" />
            <span>云端增强 (Cloud)</span>
          </div>
          <span className="text-xs text-muted-foreground">处理公开数据，调用最强云端模型。</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
