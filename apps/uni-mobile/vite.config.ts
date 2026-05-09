import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

const uniPlugin = ((uni as unknown as { default?: typeof uni }).default ?? uni) as typeof uni

export default defineConfig({
  plugins: [uniPlugin()],
})
