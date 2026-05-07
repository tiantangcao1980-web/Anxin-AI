import { describe, expect, it } from 'vitest'

import { createGraphRenderPlan, GRAPH_RENDER_LIMITS, type GraphLinkLike, type GraphNodeLike } from './graphPerformance'

function makeLargeGraph() {
  const nodes: GraphNodeLike[] = Array.from({ length: 1000 }, (_, index) => ({
    id: `n-${index}`,
    type: index % 5 === 0 ? 'law' : index % 3 === 0 ? 'document' : 'entity',
    relationCount: 1000 - index,
  }))

  const links: GraphLinkLike[] = []
  for (let index = 0; index < 1000; index += 1) {
    links.push({ source: `n-${index}`, target: `n-${(index + 1) % 1000}` })
    links.push({ source: `n-${index}`, target: `n-${(index + 7) % 1000}` })
  }
  links.push({ source: 'n-950', target: 'n-999' })

  return { nodes, links }
}

describe('createGraphRenderPlan', () => {
  it('keeps small graphs unchanged', () => {
    const nodes = [
      { id: 'a', type: 'entity', relationCount: 2 },
      { id: 'b', type: 'law', relationCount: 1 },
    ]
    const links = [{ source: 'a', target: 'b' }]

    const plan = createGraphRenderPlan(nodes, links)

    expect(plan.nodes).toEqual(nodes)
    expect(plan.links).toEqual(links)
    expect(plan.isDownsampled).toBe(false)
  })

  it('downsamples 1k node graphs and keeps selected context', () => {
    const { nodes, links } = makeLargeGraph()

    const plan = createGraphRenderPlan(nodes, links, {
      selectedNodeId: 'n-950',
      maxNodes: GRAPH_RENDER_LIMITS.maxNodes,
      maxLinks: GRAPH_RENDER_LIMITS.maxLinks,
    })

    const nodeIds = new Set(plan.nodes.map((node) => node.id))
    const linkEndpoints = plan.links.flatMap((link) => [link.source, link.target])

    expect(plan.isDownsampled).toBe(true)
    expect(plan.totalNodes).toBe(1000)
    expect(plan.nodes).toHaveLength(GRAPH_RENDER_LIMITS.maxNodes)
    expect(plan.links.length).toBeLessThanOrEqual(GRAPH_RENDER_LIMITS.maxLinks)
    expect(nodeIds.has('n-950')).toBe(true)
    expect(nodeIds.has('n-999')).toBe(true)
    expect(nodeIds.has('n-0')).toBe(true)
    expect([...nodeIds].some((id) => id.startsWith('n-') && nodes[Number(id.slice(2))]?.type === 'law')).toBe(true)
    expect(linkEndpoints.every((endpoint) => nodeIds.has(String(endpoint)))).toBe(true)
  })
})
