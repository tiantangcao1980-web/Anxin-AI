// -*- coding: utf-8 -*-
/**
 * App 全局配置（V3 P21-A）
 *
 * 主包：login + tabBar 页（home / me）+ webview 壳
 * 分包：tasks / personas / capabilities —— 由 P21-B/C/D 实际填充
 *
 * tabBar 图标 (assets/tab/*.png) 由 scripts/generate-icons.js 生成。
 *
 * 主包大小目标：< 1.5 MB（微信限制）
 * 单个分包：< 2 MB；分包总和 < 8 MB
 */
export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/me/index',
    'pages/login/index',
    'pages/webview/index',
  ],
  // 分包结构：P21-A 仅声明 tabBar 入口 page；P21-B/C/D 接入时自行追加 detail/chat/create 等子页面。
  subpackages: [
    {
      root: 'subpackages/tasks',
      pages: ['index/index', 'detail/index', 'create/index'],
    },
    {
      root: 'subpackages/personas',
      pages: ['index/index'], // P21-C 追加: detail/index, chat/index
    },
    {
      root: 'subpackages/capabilities',
      pages: ['index/index'], // P21-D 追加: scheduled-tasks/index, app-authorizations/index, skills/index, plugins/index, message-channels/index, pairing-authorizations/index
    },
  ],
  preloadRule: {
    'pages/index/index': {
      network: 'all',
      packages: ['subpackages/personas'],
    },
  },
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#FFFFFF',
    navigationBarTitleText: '安心智能助手',
    navigationBarTextStyle: 'black',
    backgroundColor: '#FAFAFA',
    enablePullDownRefresh: false,
  },
  tabBar: {
    color: '#86909C',
    selectedColor: '#D4A574',
    backgroundColor: '#FFFFFF',
    borderStyle: 'black',
    list: [
      {
        pagePath: 'pages/index/index',
        text: '智能体',
        iconPath: 'assets/tab/agents.png',
        selectedIconPath: 'assets/tab/agents-active.png',
      },
      {
        pagePath: 'subpackages/tasks/index/index',
        text: '任务',
        iconPath: 'assets/tab/tasks.png',
        selectedIconPath: 'assets/tab/tasks-active.png',
      },
      {
        pagePath: 'subpackages/capabilities/index/index',
        text: '能力',
        iconPath: 'assets/tab/capabilities.png',
        selectedIconPath: 'assets/tab/capabilities-active.png',
      },
      {
        pagePath: 'pages/me/index',
        text: '我',
        iconPath: 'assets/tab/me.png',
        selectedIconPath: 'assets/tab/me-active.png',
      },
    ],
  },
  permission: {
    'scope.userInfo': {
      desc: '用于个性化展示和工作记录',
    },
  },
  requiredPrivateInfos: [],
  lazyCodeLoading: 'requiredComponents',
})
