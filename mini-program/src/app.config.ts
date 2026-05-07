// 注意: tabBar 图标文件需要先运行 node scripts/generate-icons.js 生成
import { miniProgramTheme } from './styles/design-tokens'

export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/chat/index',
    'pages/profile/index',
  ],
  window: {
    backgroundTextStyle: 'dark',
    navigationBarBackgroundColor: miniProgramTheme.brandPrimary,
    navigationBarTitleText: '安心法务',
    navigationBarTextStyle: 'white',
    enablePullDownRefresh: false,
    backgroundColor: miniProgramTheme.background,
  },
  tabBar: {
    color: miniProgramTheme.textTertiary,
    selectedColor: miniProgramTheme.brandPrimary,
    backgroundColor: miniProgramTheme.surface,
    borderStyle: 'black',
    list: [
      {
        pagePath: 'pages/index/index',
        text: '首页',
        iconPath: 'assets/tab-home.png',
        selectedIconPath: 'assets/tab-home-active.png',
      },
      {
        pagePath: 'pages/chat/index',
        text: '咨询',
        iconPath: 'assets/tab-chat.png',
        selectedIconPath: 'assets/tab-chat-active.png',
      },
      {
        pagePath: 'pages/profile/index',
        text: '我的',
        iconPath: 'assets/tab-profile.png',
        selectedIconPath: 'assets/tab-profile-active.png',
      },
    ],
  },
})
