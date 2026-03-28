import type { UserConfigExport } from '@tarojs/cli'

export default {
  mini: {},
  h5: {
    enableExtract: true,
    miniCssExtractPluginOption: {
      ignoreOrder: true,
      filename: 'css/[name].[hash].css',
      chunkFilename: 'css/[name].[chunkhash].css',
    },
  },
  defineConstants: {
    TARO_APP_API_BASE: JSON.stringify('https://api.anxinlegal.com/api/v1'),
  },
} satisfies UserConfigExport
