import type { UserConfigExport } from '@tarojs/cli'

/**
 * H5 生产构建配置。
 *
 * 入口包瘦身策略：把 React / Taro 运行时 + 业务代码拆分到独立的 vendor
 * chunk，使应用入口（app.js）只保留业务逻辑，利用浏览器缓存。
 * 同时把 webpack performance 阈值对齐到真实目标，避免误报。
 */
export default {
  mini: {},
  h5: {
    enableExtract: true,
    miniCssExtractPluginOption: {
      ignoreOrder: true,
      filename: 'css/[name].[hash].css',
      chunkFilename: 'css/[name].[chunkhash].css',
    },
    webpackChain(chain) {
      chain.optimization.splitChunks({
        chunks: 'all',
        minSize: 20_000,
        cacheGroups: {
          // React 核心
          react: {
            name: 'vendor-react',
            test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
            priority: 30,
            enforce: true,
          },
          // Taro 运行时
          taro: {
            name: 'vendor-taro',
            test: /[\\/]node_modules[\\/]@tarojs[\\/]/,
            priority: 25,
            enforce: true,
          },
          // 其他 node_modules 依赖
          vendors: {
            name: 'vendors',
            test: /[\\/]node_modules[\\/]/,
            priority: 10,
            enforce: true,
          },
        },
      })
      // 入口总量（首次加载）目标：≤ 430 KiB 未压缩 / ~140 KiB gzip。
      // 关键是业务代码 app.js ≤ 40 KiB；vendor chunk 享受长缓存命中。
      chain.performance
        .maxEntrypointSize(430_000)
        .maxAssetSize(500_000)
        .hints('warning')
    },
  },
  defineConstants: {
    TARO_APP_API_BASE: JSON.stringify('https://api.anxinlegal.com/api/v1'),
  },
} satisfies UserConfigExport
