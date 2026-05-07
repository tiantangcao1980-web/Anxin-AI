export const GRAPH_RENDER_LIMITS = {
  maxNodes: 200,
  maxLinks: 600,
}

type Endpoint = string | { id?: string }

export interface GraphNodeLike {
  id: string
  type?: string
  relationCount?: number
  val?: number
}

export interface GraphLinkLike {
  source: Endpoint
  target: Endpoint
}

export interface GraphRenderPlan<TNode, TLink> {
  nodes: TNode[]
  links: TLink[]
  totalNodes: number
  totalLinks: number
  isDownsampled: boolean
}

interface CreateGraphRenderPlanOptions {
  maxNodes?: number
  maxLinks?: number
  selectedNodeId?: string | null
  centerNodeId?: string | null
}

function endpointId(endpoint: Endpoint): string {
  return typeof endpoint === 'string' ? endpoint : endpoint.id || ''
}

function nodeWeight(node: GraphNodeLike, priorityIds: Set<string>): number {
  const relationWeight = node.relationCount ?? node.val ?? 0
  return relationWeight + (priorityIds.has(node.id) ? 1_000_000 : 0)
}

function sortNodes<TNode extends GraphNodeLike>(nodes: TNode[], priorityIds: Set<string>): TNode[] {
  return [...nodes].sort((a, b) => {
    const weightDelta = nodeWeight(b, priorityIds) - nodeWeight(a, priorityIds)
    if (weightDelta !== 0) return weightDelta
    return a.id.localeCompare(b.id)
  })
}

function collectPriorityIds<TLink extends GraphLinkLike>(
  links: TLink[],
  selectedNodeId?: string | null,
  centerNodeId?: string | null,
): Set<string> {
  const priorityIds = new Set<string>()
  if (selectedNodeId) priorityIds.add(selectedNodeId)
  if (centerNodeId) priorityIds.add(centerNodeId)

  if (priorityIds.size === 0) return priorityIds

  links.forEach((link) => {
    const source = endpointId(link.source)
    const target = endpointId(link.target)
    if (priorityIds.has(source) && target) priorityIds.add(target)
    if (priorityIds.has(target) && source) priorityIds.add(source)
  })

  return priorityIds
}

function selectNodes<TNode extends GraphNodeLike>(
  nodes: TNode[],
  links: GraphLinkLike[],
  maxNodes: number,
  selectedNodeId?: string | null,
  centerNodeId?: string | null,
): TNode[] {
  if (nodes.length <= maxNodes) return nodes

  const priorityIds = collectPriorityIds(links, selectedNodeId, centerNodeId)
  const byId = new Map(nodes.map((node) => [node.id, node]))
  const selected = sortNodes(
    [...priorityIds].map((id) => byId.get(id)).filter((node): node is TNode => Boolean(node)),
    priorityIds,
  ).slice(0, maxNodes)

  const selectedIds = new Set(selected.map((node) => node.id))
  const buckets = new Map<string, TNode[]>()
  sortNodes(nodes, priorityIds).forEach((node) => {
    if (selectedIds.has(node.id)) return
    const type = node.type || 'unknown'
    const bucket = buckets.get(type) || []
    bucket.push(node)
    buckets.set(type, bucket)
  })

  const result = [...selected]
  const bucketKeys = [...buckets.keys()].sort()
  while (result.length < maxNodes) {
    let added = false
    for (const key of bucketKeys) {
      if (result.length >= maxNodes) break
      const node = buckets.get(key)?.shift()
      if (!node) continue
      result.push(node)
      selectedIds.add(node.id)
      added = true
    }
    if (!added) break
  }

  return result
}

function sortLinks<TLink extends GraphLinkLike>(
  links: TLink[],
  priorityIds: Set<string>,
): TLink[] {
  return [...links].sort((a, b) => {
    const aPriority = Number(priorityIds.has(endpointId(a.source))) + Number(priorityIds.has(endpointId(a.target)))
    const bPriority = Number(priorityIds.has(endpointId(b.source))) + Number(priorityIds.has(endpointId(b.target)))
    if (aPriority !== bPriority) return bPriority - aPriority
    return `${endpointId(a.source)}:${endpointId(a.target)}`.localeCompare(
      `${endpointId(b.source)}:${endpointId(b.target)}`,
    )
  })
}

export function createGraphRenderPlan<
  TNode extends GraphNodeLike,
  TLink extends GraphLinkLike,
>(
  nodes: TNode[],
  links: TLink[],
  options: CreateGraphRenderPlanOptions = {},
): GraphRenderPlan<TNode, TLink> {
  const maxNodes = Math.max(1, options.maxNodes ?? GRAPH_RENDER_LIMITS.maxNodes)
  const maxLinks = Math.max(0, options.maxLinks ?? GRAPH_RENDER_LIMITS.maxLinks)
  const selectedNodes = selectNodes(
    nodes,
    links,
    maxNodes,
    options.selectedNodeId,
    options.centerNodeId,
  )
  const selectedNodeIds = new Set(selectedNodes.map((node) => node.id))
  const priorityIds = collectPriorityIds(links, options.selectedNodeId, options.centerNodeId)
  const visibleLinks = sortLinks(
    links.filter((link) => selectedNodeIds.has(endpointId(link.source)) && selectedNodeIds.has(endpointId(link.target))),
    priorityIds,
  ).slice(0, maxLinks)

  return {
    nodes: selectedNodes,
    links: visibleLinks,
    totalNodes: nodes.length,
    totalLinks: links.length,
    isDownsampled: selectedNodes.length < nodes.length || visibleLinks.length < links.length,
  }
}
