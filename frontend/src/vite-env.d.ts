/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** V3 IA 侧边栏切换：'true' 启用 LayoutV3 + SidebarV3，否则保留旧 Layout */
  readonly VITE_V3_NAV?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
