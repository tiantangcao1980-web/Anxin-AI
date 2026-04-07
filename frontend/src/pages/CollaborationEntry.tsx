import { Navigate, useLocation, useParams } from 'react-router-dom'

export default function CollaborationEntry() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const location = useLocation()

  return (
    <Navigate
      to="/documents"
      replace
      state={{ ...location.state, entryMode: 'collaboration', sessionId }}
    />
  )
}
