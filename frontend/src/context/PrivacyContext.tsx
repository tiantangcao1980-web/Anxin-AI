import React, { createContext, useContext, useState, ReactNode } from 'react';

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
  const [mode, setMode] = useState<PrivacyMode>(PrivacyMode.HYBRID);
  const [hardwareStatus, setHardwareStatus] = useState<HardwareStatus>(HardwareStatus.DISCONNECTED);
  const [hardwareName, setHardwareName] = useState<string>('AI私有助手');
  const [secureComputeUsage, setSecureComputeUsage] = useState<number>(0);
  const [openClawInstalled, setOpenClawInstalled] = useState<boolean>(false);
  // V2: 订阅检查状态
  const [subscriptionRequired, setSubscriptionRequired] = useState<boolean>(false);

  // V2: 带订阅检查的模式切换
  const requestModeSwitch = async (targetMode: PrivacyMode): Promise<boolean> => {
    // 切到本地模式无需检查
    if (targetMode === PrivacyMode.LOCAL) {
      setMode(targetMode);
      setSubscriptionRequired(false);
      return true;
    }
    // 切到混合/云端需要检查订阅
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setSubscriptionRequired(true);
        return false;
      }
      const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003/api/v1';
      const resp = await fetch(`${API}/billing/v2/can-use-mode?mode=${targetMode.toLowerCase()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await resp.json();
      const allowed = json?.data?.allowed ?? true; // 默认允许（API 不可用时不阻断）
      if (allowed) {
        setMode(targetMode);
        setSubscriptionRequired(false);
        return true;
      } else {
        setSubscriptionRequired(true);
        return false;
      }
    } catch {
      // API 调用失败时不阻断，允许切换
      setMode(targetMode);
      return true;
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
