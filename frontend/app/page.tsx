'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { searchClients, type ClientBrief } from '@/lib/api'
import { Search, Building2, ChevronRight, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

const TYPE_COLORS: Record<string, string> = {
  Installatore: 'bg-blue-100 text-blue-700',
  Impresa:      'bg-purple-100 text-purple-700',
  Rivenditore:  'bg-amber-100 text-amber-700',
  OEM:          'bg-green-100 text-green-700',
  Quadrista:    'bg-rose-100 text-rose-700',
}

export default function HomePage() {
  const [query, setQuery] = useState('')
  const [clients, setClients] = useState<ClientBrief[]>([])
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  const load = useCallback(async (q: string) => {
    setLoading(true)
    try {
      setClients(await searchClients(q || undefined))
    } catch {
      setClients([])
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial load
  useEffect(() => { load('') }, [load])

  // Debounced search
  useEffect(() => {
    const t = setTimeout(() => load(query), 280)
    return () => clearTimeout(t)
  }, [query, load])

  return (
    <div className="max-w-xl mx-auto pt-14 px-4 pb-16">
      {/* Hero */}
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">
          Seleziona un cliente
        </h1>
        <p className="text-gray-500 text-sm">
          Cerca per nome, codice, città o provincia
        </p>
      </div>

      {/* Search input */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4 pointer-events-none" />
        {loading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4 animate-spin" />
        )}
        <input
          autoFocus
          type="search"
          placeholder="es. Rossi, C001, Milano..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="w-full pl-9 pr-9 py-2.5 border border-gray-300 rounded-xl text-sm
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     bg-white shadow-sm placeholder:text-gray-400"
        />
      </div>

      {/* Client list */}
      <div className="space-y-2 animate-fade-in">
        {clients.map(c => (
          <button
            key={c.client_code}
            onClick={() => router.push(`/cockpit/${c.client_code}`)}
            className="w-full flex items-center justify-between p-4 bg-white border border-gray-200
                       rounded-xl hover:border-blue-400 hover:shadow-md transition-all text-left group"
          >
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                <Building2 className="w-4 h-4 text-blue-600" />
              </div>
              <div className="min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {c.client_name ?? c.client_code}
                </p>
                <p className="text-xs text-gray-500 truncate">
                  {c.client_code}
                  {c.city ? ` · ${c.city}` : ''}
                  {c.province ? ` (${c.province})` : ''}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0 ml-3">
              {c.client_type && (
                <span className={cn(
                  'hidden sm:inline-flex text-xs font-medium px-2 py-0.5 rounded-full',
                  TYPE_COLORS[c.client_type] ?? 'bg-gray-100 text-gray-600'
                )}>
                  {c.client_type}
                </span>
              )}
              <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
            </div>
          </button>
        ))}

        {!loading && clients.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <Search className="w-8 h-8 mx-auto mb-2 opacity-40" />
            <p className="text-sm">Nessun cliente trovato per &ldquo;{query}&rdquo;</p>
          </div>
        )}
      </div>
    </div>
  )
}
