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
  toggleHardwareConnection: () => void;
  setOpenClawInstalled: (installed: boolean) => void;
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
        toggleHardwareConnection,
        setOpenClawInstalled,
      }}
    >
      {children}
    </PrivacyContext.Provider>
  );
};
