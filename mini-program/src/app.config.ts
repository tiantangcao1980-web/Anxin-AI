export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/chat/index',
    'pages/profile/index',
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#D4A574',
    navigationBarTitleText: '安心法务',
    navigationBarTextStyle: 'white',
  },
  tabBar: {
    color: '#999999',
    selectedColor: '#D4A574',
    backgroundColor: '#ffffff',
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
