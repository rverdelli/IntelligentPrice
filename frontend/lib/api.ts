// All types mirror backend/app/schemas.py

export interface ClientBrief {
  client_code: string
  client_name: string | null
  client_type: string | null
  branch: string | null
  city: string | null
  province: string | null
}

export interface ArticleBrief {
  article_code: string
  article_desc: string | null
  sco_code: string
  sco_desc: string | null
}

export interface CartelliniItem {
  sco_code: string
  sco_desc: string | null
  contract_discount_pct: number
}

export interface OfferBrief {
  offer_num: string
  article_code: string
  article_desc: string | null
  offer_date: string | null
  qty: number | null
  list_price: number | null
  net_price: number | null
  discount_pct: number | null
  row_status: string | null
}

export interface ClientContext {
  client_code: string
  client_name: string | null
  client_type: string | null
  branch: string | null
  city: string | null
  province: string | null
  agent: string | null
  potential: string | null
  num_employees: number | null
  cartellini: CartelliniItem[]
  recent_offers: OfferBrief[]
}

export interface ExplanationStep {
  step: string
  pool_size: number
  median_discount: number | null
  used: boolean
  detail: string | null
}

export interface ActivePromo {
  promo_id: string
  promo_type: string
}

export interface RecommendResponse {
  client_code: string
  article_code: string
  qty: number
  suggested_discount_pct: number
  min_discount_pct: number
  max_discount_pct: number
  contract_floor_pct: number | null
  expected_margin_pct: number
  expected_margin_eur: number
  unit_cost_used: number
  list_price_used: number
  requires_deroga: boolean
  active_promo: ActivePromo | null
  explanation_trace: ExplanationStep[]
  data_sufficiency: 'high' | 'medium' | 'low' | 'insufficient'
}

// Use the Next.js rewrite proxy (/api → localhost:8000)
const BASE = '/api'

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? 'Errore server')
  }
  return res.json() as Promise<T>
}

export function searchClients(search?: string): Promise<ClientBrief[]> {
  const q = search ? `&search=${encodeURIComponent(search)}` : ''
  return apiFetch(`/catalog/clients?limit=30${q}`)
}

export function searchArticles(search?: string, withHistory = false): Promise<ArticleBrief[]> {
  const params = new URLSearchParams({ limit: '30' })
  if (search) params.set('search', search)
  if (withHistory) params.set('with_history', 'true')
  return apiFetch(`/catalog/articles?${params}`)
}

export function getClientContext(code: string): Promise<ClientContext> {
  return apiFetch(`/clients/${encodeURIComponent(code)}/context`)
}

export function getRecommendations(
  clientCode: string,
  items: { article_code: string; qty: number }[],
): Promise<RecommendResponse[]> {
  return apiFetch('/pricing/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_code: clientCode, items }),
  })
}
