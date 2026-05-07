import { Dimensions, Platform, StatusBar } from 'react-native'

const { width, height } = Dimensions.get('window')

export const Layout = {
  window: { width, height },
  isSmallDevice: width < 375,
  statusBarHeight: Platform.OS === 'ios' ? 44 : StatusBar.currentHeight || 0,
  tabBarBaseHeight: 56,
  tabBarHeight: Platform.OS === 'ios' ? 83 : 56,
  headerHeight: 56,
  touchTarget: {
    min: 44,
    hitSlop: 8,
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
  },
  borderRadius: {
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    full: 9999,
  },
  fontSize: {
    xs: 12,
    sm: 14,
    md: 16,
    lg: 18,
    xl: 20,
    xxl: 24,
    title: 28,
  },
}
