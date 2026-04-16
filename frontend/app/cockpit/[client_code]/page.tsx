'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  getClientContext, searchArticles, getRecommendations,
  type ClientContext, type ArticleBrief, type RecommendResponse,
} from '@/lib/api'
import { RecommendationCard } from '@/components/cockpit/recommendation-card'
import { pct, cn } from '@/lib/utils'
import {
  ArrowLeft, Search, Plus, Loader2, User, MapPin,
  Briefcase, ShieldCheck, ReceiptText,
} from 'lucide-react'

interface BasketItem {
  article: ArticleBrief
  qty: number
}

const TYPE_COLORS: Record<string, string> = {
  Installatore: 'bg-blue-100 text-blue-700',
  Impresa:      'bg-purple-100 text-purple-700',
  Rivenditore:  'bg-amber-100 text-amber-700',
  OEM:          'bg-green-100 text-green-700',
  Quadrista:    'bg-rose-100 text-rose-700',
}

export default function CockpitPage() {
  const { client_code } = useParams<{ client_code: string }>()
  const router = useRouter()

  // Client context
  const [ctx, setCtx] = useState<ClientContext | null>(null)
  const [ctxError, setCtxError] = useState<string | null>(null)

  // Article search
  const [artQuery, setArtQuery] = useState('')
  const [artResults, setArtResults] = useState<ArticleBrief[]>([])
  const [artLoading, setArtLoading] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const [qty, setQty] = useState(1)
  const searchRef = useRef<HTMLDivElement>(null)

  // Basket + recommendations
  const [basket, setBasket] = useState<BasketItem[]>([])
  const [recommendations, setRecommendations] = useState<Record<string, RecommendResponse>>({})
  const [recLoading, setRecLoading] = useState(false)
  const [recError, setRecError] = useState<string | null>(null)

  // Load client context
  useEffect(() => {
    getClientContext(client_code)
      .then(setCtx)
      .catch(e => setCtxError(e.message))
  }, [client_code])

  // Debounced article search
  useEffect(() => {
    if (!artQuery.trim()) { setArtResults([]); setShowDropdown(false); return }
    setArtLoading(true)
    const t = setTimeout(async () => {
      try {
        const res = await searchArticles(artQuery)
        setArtResults(res)
        setShowDropdown(true)
      } finally {
        setArtLoading(false)
      }
    }, 250)
    return () => clearTimeout(t)
  }, [artQuery])

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const addArticle = useCallback((art: ArticleBrief) => {
    setBasket(prev => {
      if (prev.some(b => b.article.article_code === art.article_code)) return prev
      return [...prev, { article: art, qty }]
    })
    setArtQuery('')
    setShowDropdown(false)
  }, [qty])

  const removeArticle = useCallback((code: string) => {
    setBasket(prev => prev.filter(b => b.article.article_code !== code))
    setRecommendations(prev => { const n = { ...prev }; delete n[code]; return n })
  }, [])

  const calcRecommendations = useCallback(async () => {
    if (basket.length === 0) return
    setRecLoading(true)
    setRecError(null)
    try {
      const items = basket.map(b => ({ article_code: b.article.article_code, qty: b.qty }))
      const results = await getRecommendations(client_code, items)
      const map: Record<string, RecommendResponse> = {}
      results.forEach(r => { map[r.article_code] = r })
      setRecommendations(map)
    } catch (e: unknown) {
      setRecError(e instanceof Error ? e.message : 'Errore nel calcolo')
    } finally {
      setRecLoading(false)
    }
  }, [basket, client_code])

  if (ctxError) {
    return (
      <div className="flex flex-col items-center justify-center pt-24 text-gray-500">
        <p className="text-red-500 font-medium mb-2">{ctxError}</p>
        <button onClick={() => router.push('/')} className="text-sm text-blue-600 hover:underline">
          ← Torna alla ricerca
        </button>
      </div>
    )
  }

  if (!ctx) {
    return (
      <div className="flex items-center justify-center pt-24">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="flex flex-col lg:flex-row min-h-screen">

      {/* ── LEFT SIDEBAR ─────────────────────────────────────────────── */}
      <aside className="w-full lg:w-72 xl:w-80 bg-white border-b lg:border-b-0 lg:border-r border-gray-200 p-5 shrink-0">
        <button
          onClick={() => router.push('/')}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-600 transition-colors mb-5"
        >
          <ArrowLeft className="w-4 h-4" /> Clienti
        </button>

        {/* Client name & type */}
        <div className="mb-4">
          <h2 className="text-lg font-bold text-gray-900 leading-tight">
            {ctx.client_name ?? ctx.client_code}
          </h2>
          <p className="text-sm text-gray-400 font-mono mt-0.5">{ctx.client_code}</p>
          {ctx.client_type && (
            <span className={cn(
              'inline-flex mt-2 text-xs font-medium px-2.5 py-1 rounded-full',
              TYPE_COLORS[ctx.client_type] ?? 'bg-gray-100 text-gray-600'
            )}>
              {ctx.client_type}
            </span>
          )}
        </div>

        {/* Client details */}
        <div className="space-y-2 text-sm border-t border-gray-100 pt-4 mb-4">
          {ctx.branch && (
            <div className="flex items-center gap-2 text-gray-600">
              <Briefcase className="w-3.5 h-3.5 text-gray-400 shrink-0" />
              {ctx.branch}
            </div>
          )}
          {(ctx.city || ctx.province) && (
            <div className="flex items-center gap-2 text-gray-600">
              <MapPin className="w-3.5 h-3.5 text-gray-400 shrink-0" />
              {[ctx.city, ctx.province && `(${ctx.province})`].filter(Boolean).join(' ')}
            </div>
          )}
          {ctx.agent && (
            <div className="flex items-center gap-2 text-gray-600">
              <User className="w-3.5 h-3.5 text-gray-400 shrink-0" />
              Agente: {ctx.agent}
            </div>
          )}
          {ctx.potential && (
            <div className="flex items-center gap-2 text-gray-600">
              <Briefcase className="w-3.5 h-3.5 text-gray-400 shrink-0" />
              Potenziale: {ctx.potential}
            </div>
          )}
        </div>

        {/* Cartellini */}
        {ctx.cartellini.length > 0 && (
          <div className="border-t border-gray-100 pt-4 mb-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex items-center gap-1 mb-2">
              <ShieldCheck className="w-3.5 h-3.5" /> Cartellini (floor sconti)
            </p>
            <div className="space-y-1.5">
              {ctx.cartellini.map(c => (
                <div key={c.sco_code} className="flex justify-between items-center text-sm">
                  <span className="text-gray-600 truncate mr-2">
                    {c.sco_desc ?? c.sco_code}
                  </span>
                  <span className="font-semibold text-blue-700 shrink-0">
                    {pct(c.contract_discount_pct)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent offers */}
        {ctx.recent_offers.length > 0 && (
          <div className="border-t border-gray-100 pt-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex items-center gap-1 mb-2">
              <ReceiptText className="w-3.5 h-3.5" /> Ultime offerte
            </p>
            <div className="space-y-1">
              {ctx.recent_offers.slice(0, 5).map(o => (
                <div key={o.offer_num} className="flex justify-between text-xs text-gray-600">
                  <span className="truncate mr-2">{o.article_desc ?? o.article_code}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    {o.discount_pct != null && (
                      <span className="font-medium">{pct(o.discount_pct)}</span>
                    )}
                    <span className={cn(
                      'px-1.5 py-0.5 rounded text-xs',
                      o.row_status === 'ACC' ? 'bg-green-100 text-green-700' :
                      o.row_status === 'PER' ? 'bg-red-100 text-red-600' :
                      'bg-gray-100 text-gray-500'
                    )}>
                      {o.row_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </aside>

      {/* ── MAIN AREA ─────────────────────────────────────────────────── */}
      <div className="flex-1 p-5 lg:p-6 space-y-5 max-w-3xl">

        {/* Article search bar */}
        <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
          <p className="text-sm font-medium text-gray-700 mb-3">Aggiungi articolo</p>
          <div className="flex gap-2 flex-wrap">
            {/* Article search */}
            <div className="relative flex-1 min-w-48" ref={searchRef}>
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4 pointer-events-none" />
              {artLoading && (
                <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4 animate-spin" />
              )}
              <input
                type="search"
                placeholder="Cerca articolo per codice o descrizione..."
                value={artQuery}
                onChange={e => setArtQuery(e.target.value)}
                onFocus={() => artResults.length > 0 && setShowDropdown(true)}
                className="w-full pl-9 pr-9 py-2 border border-gray-300 rounded-lg text-sm
                           focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {/* Dropdown */}
              {showDropdown && artResults.length > 0 && (
                <div className="absolute z-50 left-0 right-0 top-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
                  {artResults.map(a => (
                    <button
                      key={a.article_code}
                      onMouseDown={() => addArticle(a)}
                      className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-blue-50 text-left text-sm transition-colors"
                    >
                      <div>
                        <p className="font-medium text-gray-900">{a.article_desc ?? a.article_code}</p>
                        <p className="text-xs text-gray-400">{a.article_code} · {a.sco_desc ?? a.sco_code}</p>
                      </div>
                      <Plus className="w-4 h-4 text-blue-400 shrink-0 ml-2" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Qty */}
            <div className="flex items-center gap-2 shrink-0">
              <label className="text-sm text-gray-500">Qtà</label>
              <input
                type="number"
                min={1}
                value={qty}
                onChange={e => setQty(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-20 border border-gray-300 rounded-lg px-2.5 py-2 text-sm text-center
                           focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Basket summary */}
          {basket.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2 items-center">
              {basket.map(b => (
                <span
                  key={b.article.article_code}
                  className="inline-flex items-center gap-1.5 bg-blue-50 text-blue-800 text-xs px-2.5 py-1 rounded-full"
                >
                  {b.article.article_desc ?? b.article.article_code}
                  <span className="text-blue-500">× {b.qty}</span>
                  <button
                    onClick={() => removeArticle(b.article.article_code)}
                    className="text-blue-400 hover:text-red-500 transition-colors leading-none"
                  >×</button>
                </span>
              ))}
              <button
                onClick={calcRecommendations}
                disabled={recLoading}
                className="ml-auto flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60
                           text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
              >
                {recLoading
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Calcolo...</>
                  : <>Calcola sconto</>
                }
              </button>
            </div>
          )}
        </div>

        {/* Error */}
        {recError && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
            {recError}
          </div>
        )}

        {/* Recommendation cards */}
        {basket.map(b => {
          const rec = recommendations[b.article.article_code]
          if (!rec) return null
          return (
            <RecommendationCard
              key={b.article.article_code}
              rec={rec}
              articleDesc={b.article.article_desc}
              scoDesc={b.article.sco_desc}
              onRemove={() => removeArticle(b.article.article_code)}
            />
          )
        })}

        {/* Empty state */}
        {basket.length === 0 && (
          <div className="text-center pt-16 text-gray-400">
            <Search className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p className="font-medium">Nessun articolo selezionato</p>
            <p className="text-sm mt-1">Cerca un articolo e aggiungi la quantità per calcolare lo sconto</p>
          </div>
        )}
      </div>
    </div>
  )
}
