import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Banner } from '../components/Banner'
import { Card } from '../components/Card'
import { fetchAudit } from '../features/lots'

function integrityLabel(status: string): string {
  if (status === 'VERIFIED') return 'Verified'
  if (status === 'TAMPERED') return 'Changes detected'
  return 'Unable to verify'
}

export function Audit() {
  const { id = '' } = useParams()
  const q = useQuery({
    queryKey: ['audit', id],
    queryFn: () => fetchAudit(id),
  })

  const verification = q.data?.verification

  return (
    <div className="space-y-4">
      <Link to={`/lots/${id}`} className="text-sm text-brand hover:underline">← Back to lot</Link>
      <h1 className="text-2xl font-semibold">Public audit</h1>
      {q.isLoading && <p>Loading…</p>}
      {verification && (
        <Banner
          variant={
            verification.status === 'VERIFIED'
              ? 'success'
              : verification.status === 'TAMPERED'
                ? 'danger'
                : 'warning'
          }
        >
          {integrityLabel(verification.status ?? '')}
          {verification.checked_at && (
            <span className="ml-2 text-xs opacity-80">
              {new Date(verification.checked_at).toLocaleString()}
            </span>
          )}
        </Banner>
      )}
      <Card>
        <ul className="space-y-2 text-sm">
          {q.data?.items.map((ev) => (
            <li key={ev.sequence}>
              #{ev.sequence} {ev.type}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
