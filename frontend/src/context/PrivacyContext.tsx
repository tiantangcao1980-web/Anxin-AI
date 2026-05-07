import React, { createContext, useContext, useState, ReactNode } from 'react';
import { buildApiHeaders, setApiPrivacyMode } from '@/lib/api';
import { getTokenStorage } from '@/lib/platform/storage';

export enum PrivacyMode {
  LOCAL = 'LOCAL', // L1
  HYBRID = 'HYBRID', // L2
  CLOUD = 'CLOUD', // L3
}

export enum HardwareStatus {
  CONNECTED = 'CONNECTED',
  DISCONNECTED = 'DISCONNECTED',
  BUSY = 'BUSY',
}

interface PrivacyState {
  mode: PrivacyMode;
  hardwareStatus: HardwareStatus;
  hardwareName: string;
  secureComputeUsage: number; // 0-100%
  openClawInstalled: boolean; // OpenClaw 是否已安装
}

interface PrivacyContextType extends PrivacyState {
  setMode: (mode: PrivacyMode) => void;
  /** V2: 尝试切换模式，非本地模式需检查订阅 */
  requestModeSwitch: (mode: PrivacyMode) => Promise<boolean>;
  toggleHardwareConnection: () => void;
  setOpenClawInstalled: (installed: boolean) => void;
  /** V2: 模式切换被订阅拒绝时的回调 */
  subscriptionRequired: boolean;
  setSubscriptionRequired: (v: boolean) => void;
}

const PrivacyContext = createContext<PrivacyContextType | undefined>(undefined);

export const usePrivacy = () => {
  const context = useContext(PrivacyContext);
  if (!context) {
    throw new Error('usePrivacy must be used within a PrivacyProvider');
  }
  return context;
};

export const PrivacyProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [mode, setModeState] = useState<PrivacyMode>(PrivacyMode.HYBRID);
  const [hardwareStatus, setHardwareStatus] = useState<HardwareStatus>(HardwareStatus.DISCONNECTED);
  const [hardwareName, setHardwareName] = useState<string>('AI私有助手');
  const [secureComputeUsage, setSecureComputeUsage] = useState<number>(0);
  const [openClawInstalled, setOpenClawInstalled] = useState<boolean>(false);
  // V2: 订阅检查状态
  const [subscriptionRequired, setSubscriptionRequired] = useState<boolean>(false);
  const setMode = React.useCallback((nextMode: PrivacyMode) => {
    setApiPrivacyMode(nextMode);
    setModeState(nextMode);
  }, []);

  // V2: 带订阅检查的模式切换 — fail-closed
  // 任何无法证明用户有权访问目标模式的情况，都拒绝切换并提示订阅。
  const requestModeSwitch = async (targetMode: PrivacyMode): Promise<boolean> => {
    // 切到本地模式无需检查
    if (targetMode === PrivacyMode.LOCAL) {
      setMode(targetMode);
      setSubscriptionRequired(false);
      return true;
    }
    // 切到混合/云端需要检查订阅
    try {
      const token = await getTokenStorage().getAccessToken();
      if (!token) {
        setSubscriptionRequired(true);
        return false;
      }
      // 默认 8001 与后端 uvicorn 端口一致；生产由 VITE_API_BASE_URL 覆盖为相对 /api/v1
      const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';
      const resp = await fetch(`${API}/billing/v2/can-use-mode?mode=${targetMode.toLowerCase()}`, {
        headers: buildApiHeaders(undefined, { token, privacyMode: targetMode }),
      });
      if (!resp.ok) {
        // 非 2xx：不允许切换（fail-closed），提示订阅
        setSubscriptionRequired(true);
        return false;
      }
      const json = await resp.json();
      // S-审计修复：默认值改为 false（fail-closed），缺字段也按拒绝处理
      const allowed = json?.data?.allowed ?? false;
      if (allowed) {
        setMode(targetMode);
        setSubscriptionRequired(false);
        return true;
      }
      setSubscriptionRequired(true);
      return false;
    } catch {
      // API 调用失败时不允许切换（fail-closed）
      setSubscriptionRequired(true);
      return false;
    }
  };

  // 模拟硬件连接和算力变化
  const toggleHardwareConnection = () => {
    if (hardwareStatus === HardwareStatus.CONNECTED) {
      setHardwareStatus(HardwareStatus.DISCONNECTED);
      setSecureComputeUsage(0);
      if (mode === PrivacyMode.LOCAL) {
        setMode(PrivacyMode.HYBRID); // 硬件断开时降级
      }
    } else {
      setHardwareStatus(HardwareStatus.CONNECTED);
      setSecureComputeUsage(35); // 模拟初始负载
    }
  };

  // 模拟算力波动
  React.useEffect(() => {
    if (hardwareStatus !== HardwareStatus.CONNECTED) return;
    
    const interval = setInterval(() => {
      setSecureComputeUsage(prev => {
        const change = Math.random() * 10 - 5;
        return Math.min(Math.max(prev + change, 10), 90);
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [hardwareStatus]);

  return (
    <PrivacyContext.Provider
      value={{
        mode,
        hardwareStatus,
        hardwareName,
        secureComputeUsage,
        openClawInstalled,
        setMode,
        requestModeSwitch,
        toggleHardwareConnection,
        setOpenClawInstalled,
        subscriptionRequired,
        setSubscriptionRequired,
      }}
    >
      {children}
    </PrivacyContext.Provider>
  );
};
