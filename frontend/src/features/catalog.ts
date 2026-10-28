import { api } from '../lib/http'

export type CatalogItem = {
  external_id: string
  title: string
  artist: string | null
  image_url: string | null
}

export async function searchCatalog(
  q: string,
  offset = 0,
  limit = 10,
  signal?: AbortSignal,
) {
  return api<{ items: CatalogItem[]; total: number }>(
    `/catalog/search?q=${encodeURIComponent(q)}&offset=${offset}&limit=${limit}`,
    { signal },
  )
}
