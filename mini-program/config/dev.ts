import type { UserConfigExport } from '@tarojs/cli'

export default {
  logger: {
    quiet: false,
    stats: true,
  },
  mini: {},
  h5: {},
  defineConstants: {
    TARO_APP_API_BASE: JSON.stringify('http://localhost:8001/api/v1'),
  },
} satisfies UserConfigExport
