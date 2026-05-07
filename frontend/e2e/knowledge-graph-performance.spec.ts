import { expect, test, type Page, type TestInfo } from '@playwright/test'

import { installApiMocks, seedAuthState } from './helpers/session'

function makeLargeGraph() {
  const nodes = Array.from({ length: 1000 }, (_, index) => ({
    id: `node-${index}`,
    label: `图谱节点 ${index}`,
    type: index % 5 === 0 ? 'law' : index % 3 === 0 ? 'document' : 'entity',
  }))
  const edges = Array.from({ length: 2200 }, (_, index) => ({
    source: `node-${index % 1000}`,
    target: `node-${(index * 7 + 13) % 1000}`,
    relation: index % 2 === 0 ? 'REFERENCES' : 'RELATED_TO',
    label: index % 2 === 0 ? '引用' : '相关',
  }))

  return { nodes, edges, total: nodes.length }
}

async function expectGraphCanvasPainted(page: Page, testInfo: TestInfo, name: string) {
  const container = page.getByTestId('knowledge-graph-canvas')
  await expect(container).toHaveAttribute('data-downsampled', 'true')
  await expect
    .poll(async () => Number(await container.getAttribute('data-rendered-nodes')))
    .toBeLessThanOrEqual(200)
  await expect
    .poll(async () => Number(await container.getAttribute('data-rendered-links')))
    .toBeLessThanOrEqual(600)

  const canvas = container.locator('canvas').first()
  await expect(canvas).toBeVisible({ timeout: 15_000 })
  await page.waitForTimeout(800)

  const sample = await canvas.evaluate((element) => {
    const canvasElement = element as HTMLCanvasElement
    const context = canvasElement.getContext('2d')
    if (!context) return { width: canvasElement.width, height: canvasElement.height, changed: 0 }

    const { width, height } = canvasElement
    const image = context.getImageData(0, 0, width, height).data
    const base = [image[0], image[1], image[2]]
    let changed = 0
    const stride = 64
    for (let index = 0; index < image.length; index += stride) {
      const delta =
        Math.abs(image[index] - base[0]) +
        Math.abs(image[index + 1] - base[1]) +
        Math.abs(image[index + 2] - base[2])
      if (delta > 32) changed += 1
    }
    return { width, height, changed }
  })

  expect(sample.width).toBeGreaterThan(100)
  expect(sample.height).toBeGreaterThan(100)
  expect(sample.changed).toBeGreaterThan(50)

  const fps = await page.evaluate(
    () =>
      new Promise<number>((resolve) => {
        let frames = 0
        const start = performance.now()
        const tick = (now: number) => {
          frames += 1
          if (now - start >= 1000) {
            resolve((frames * 1000) / (now - start))
            return
          }
          requestAnimationFrame(tick)
        }
        requestAnimationFrame(tick)
      }),
  )
  expect(fps).toBeGreaterThanOrEqual(30)

  await page.screenshot({ path: testInfo.outputPath(`${name}.png`), fullPage: false })
}

test.describe('知识图谱大图降级', () => {
  test.beforeEach(async ({ page }) => {
    const largeGraph = makeLargeGraph()
    await installApiMocks(page, {
      graph: {
        overview: {
          available: true,
          total_nodes: largeGraph.nodes.length,
          total_edges: largeGraph.edges.length,
          node_types: { entity: 533, law: 200, document: 267 },
          relation_types: { REFERENCES: 1100, RELATED_TO: 1100 },
        },
        types: [
          { type: 'entity', count: 533, color: '#2563eb' },
          { type: 'law', count: 200, color: '#16a34a' },
          { type: 'document', count: 267, color: '#ea580c' },
        ],
        search: largeGraph,
      },
    })
    await seedAuthState(page, {
      role: 'enterprise_user',
      name: '企业法务',
      email: 'enterprise@example.com',
    })
  })

  test('1k 节点图谱在桌面和移动视口下自动降采样且 canvas 非空', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 920 })
    await page.goto('/knowledge-graph')
    await expectGraphCanvasPainted(page, testInfo, 'knowledge-graph-1k-desktop')

    await page.setViewportSize({ width: 390, height: 844 })
    await page.reload()
    await expectGraphCanvasPainted(page, testInfo, 'knowledge-graph-1k-mobile')
  })
})
