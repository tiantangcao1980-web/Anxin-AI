import { useEffect, useMemo, useState } from 'react'
import { collaborationApi, type CollaborationSession, type CollaborationSnapshot } from '@/lib/api'

interface CollaboratorItem {
  id: string
  name: string
  role: string
}

interface CollaborationActivityItem {
  id: string
  label: string
  description: string
  targetText?: string
}

export function useCollaborationSession(
  entryMode: 'library' | 'collaboration' | 'chat',
  sessionId?: string | null,
) {
  const fallbackCollaborators = useMemo<CollaboratorItem[]>(
    () => (
      entryMode === 'collaboration'
        ? [
            { id: 'owner', name: '发起人', role: 'owner' },
            { id: 'reviewer', name: '审阅律师', role: 'commenter' },
          ]
        : []
    ),
    [entryMode],
  )
  const [collaborators, setCollaborators] = useState<CollaboratorItem[]>(fallbackCollaborators)
  const [session, setSession] = useState<CollaborationSession | null>(null)
  const [versions, setVersions] = useState<CollaborationSnapshot[]>([])
  const [activityItems, setActivityItems] = useState<CollaborationActivityItem[]>([])
  const [restoringSnapshotId, setRestoringSnapshotId] = useState<string | null>(null)

  useEffect(() => {
    if (entryMode !== 'collaboration' || !sessionId) {
      setCollaborators(fallbackCollaborators)
      setSession(null)
      setVersions([])
      setActivityItems([])
      setRestoringSnapshotId(null)
      return
    }

    let cancelled = false

    const loadCollaborationData = async () => {
      try {
        const [sessionData, items, snapshots] = await Promise.all([
          collaborationApi.getSession(sessionId),
          collaborationApi.getCollaborators(sessionId),
          collaborationApi.listSnapshots(sessionId, 10),
        ])
        if (cancelled) return
        setSession(sessionData)
        const normalized = Array.isArray(items)
          ? items.map((item) => ({
              id: item.id,
              name: item.nickname || item.user_id || '协作者',
              role: item.role,
            }))
          : []
        setCollaborators(normalized.length > 0 ? normalized : fallbackCollaborators)
        setVersions(Array.isArray(snapshots) ? snapshots : [])
      } catch {
        if (!cancelled) {
          setCollaborators(fallbackCollaborators)
          setSession(null)
          setVersions([])
          setActivityItems([])
        }
      }
    }

    void loadCollaborationData()

    return () => {
      cancelled = true
    }
  }, [entryMode, fallbackCollaborators, sessionId])

  const restoreVersion = async (snapshot: CollaborationSnapshot) => {
    if (!sessionId) return null

    setRestoringSnapshotId(snapshot.id)
    try {
      const result = await collaborationApi.restoreSnapshot(sessionId, snapshot.id)
      const newVersion = result?.new_version ?? result?.newVersion ?? session?.current_version ?? snapshot.version
      const restoredFromVersion = result?.restored_from_version ?? result?.restoredFromVersion ?? snapshot.version

      setSession((current) => (
        current
          ? {
              ...current,
              current_version: newVersion,
              last_activity_at: new Date().toISOString(),
            }
          : current
      ))
      setActivityItems((current) => [
        {
          id: `restore-${snapshot.id}-${newVersion}`,
          label: '恢复版本',
          description: `已从版本 ${restoredFromVersion} 恢复到版本 ${newVersion}`,
        },
        ...current,
      ])

      return {
        newVersion,
        restoredFromVersion,
      }
    } finally {
      setRestoringSnapshotId(null)
    }
  }

  return {
    defaultTab: entryMode === 'collaboration' ? 'collaboration' : 'ai',
    session,
    collaborators,
    comments: [],
    versions,
    activityItems,
    restoringSnapshotId,
    restoreVersion,
  }
}
