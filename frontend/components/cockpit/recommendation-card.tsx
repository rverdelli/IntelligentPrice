'use client'

import { type RecommendResponse } from '@/lib/api'
import { ExplanationTrace } from './explanation-trace'
import { pct, eur, cn } from '@/lib/utils'
import {
  TrendingUp, AlertTriangle, Tag, ShieldAlert, CheckCircle,
  BarChart2,
} from 'lucide-react'

const SUFFICIENCY_CONFIG = {
  high:         { label: 'Dato affidabile',   color: 'bg-green-100 text-green-700',  dot: 'bg-green-500' },
  medium:       { label: 'Dato medio',        color: 'bg-yellow-100 text-yellow-700', dot: 'bg-yellow-500' },
  low:          { label: 'Dato scarso',       color: 'bg-orange-100 text-orange-700', dot: 'bg-orange-500' },
  insufficient: { label: 'Dati insufficienti', color: 'bg-red-100 text-red-700',     dot: 'bg-red-500' },
}

interface Props {
  rec: RecommendResponse
  articleDesc: string | null
  scoDesc: string | null
  onRemove: () => void
}

export function RecommendationCard({ rec, articleDesc, scoDesc, onRemove }: Props) {
  const sc = SUFFICIENCY_CONFIG[rec.data_sufficiency]

  // Position of suggested discount on the min–max bar (0–100%)
  const range = rec.max_discount_pct - rec.min_discount_pct
  const pos = range > 0
    ? Math.min(100, Math.max(0, ((rec.suggested_discount_pct - rec.min_discount_pct) / range) * 100))
    : 50

  const netPrice = rec.list_price_used * (1 - rec.suggested_discount_pct)
  const isFloorApplied =
    rec.contract_floor_pct != null &&
    Math.abs(rec.suggested_discount_pct - rec.contract_floor_pct) < 0.001

  return (
    <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between px-5 pt-4 pb-3 border-b border-gray-100">
        <div>
          <p className="font-semibold text-gray-900 leading-tight">
            {articleDesc ?? rec.article_code}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-gray-400 font-mono">{rec.article_code}</span>
            {scoDesc && (
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                {scoDesc}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={onRemove}
          className="text-gray-300 hover:text-red-400 transition-colors text-lg leading-none mt-0.5"
          aria-label="Rimuovi"
        >×</button>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Promo alert */}
        {rec.active_promo && (
          <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-sm text-amber-800">
            <Tag className="w-4 h-4 shrink-0" />
            <span>
              <strong>Promo {rec.active_promo.promo_id}</strong>:{' '}
              {rec.active_promo.promo_type} — valutare con il cliente
            </span>
          </div>
        )}

        {/* Insufficient data warning */}
        {rec.data_sufficiency === 'insufficient' && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm text-red-700">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Dati insufficienti — valore stimato su media globale</span>
          </div>
        )}

        {/* Main numbers */}
        <div className="flex items-end gap-6">
          {/* Suggested discount — hero number */}
          <div>
            <p className="text-xs text-gray-500 mb-0.5 uppercase tracking-wide font-medium">
              Sconto suggerito
            </p>
            <p className="text-4xl font-bold text-gray-900 leading-none">
              {pct(rec.suggested_discount_pct)}
            </p>
            {isFloorApplied && (
              <p className="text-xs text-blue-600 mt-1 flex items-center gap-1">
                <CheckCircle className="w-3 h-3" />
                Allineato al floor contrattuale
              </p>
            )}
          </div>

          {/* Net price */}
          <div className="pb-0.5">
            <p className="text-xs text-gray-500 mb-0.5">Prezzo netto</p>
            <p className="text-xl font-semibold text-gray-700">{eur(netPrice)}</p>
            <p className="text-xs text-gray-400">su listino {eur(rec.list_price_used)}</p>
          </div>
        </div>

        {/* Range bar */}
        <div>
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>min {pct(rec.min_discount_pct)}</span>
            <span className="flex items-center gap-1">
              <BarChart2 className="w-3 h-3" /> range storico
            </span>
            <span>max {pct(rec.max_discount_pct)}</span>
          </div>
          <div className="relative h-3 bg-gray-100 rounded-full">
            {/* Filled portion */}
            <div
              className="absolute left-0 top-0 h-full rounded-full bg-blue-100"
              style={{ width: `${pos}%` }}
            />
            {/* Thumb */}
            <div
              className="absolute top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full bg-blue-600 border-2 border-white shadow"
              style={{ left: `calc(${pos}% - 7px)` }}
            />
            {/* Floor marker */}
            {rec.contract_floor_pct != null && (() => {
              const floorPos = range > 0
                ? Math.min(100, Math.max(0,
                    ((rec.contract_floor_pct - rec.min_discount_pct) / range) * 100
                  ))
                : 0
              return (
                <div
                  className="absolute top-0 h-full w-0.5 bg-blue-400 opacity-60"
                  style={{ left: `${floorPos}%` }}
                  title={`Floor: ${pct(rec.contract_floor_pct)}`}
                />
              )
            })()}
          </div>
        </div>

        {/* Floor & margin row */}
        <div className="flex flex-wrap gap-3">
          {/* Contract floor */}
          <div className={cn(
            'flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs flex-1 min-w-0',
            rec.contract_floor_pct != null
              ? 'bg-blue-50 text-blue-800'
              : 'bg-gray-50 text-gray-500'
          )}>
            <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
            <div>
              <p className="font-medium">Floor contrattuale</p>
              <p className="font-bold text-sm">
                {rec.contract_floor_pct != null
                  ? pct(rec.contract_floor_pct)
                  : 'non definito'}
              </p>
            </div>
          </div>

          {/* Margin */}
          <div className="flex items-center gap-1.5 bg-green-50 text-green-800 rounded-lg px-3 py-2 text-xs flex-1 min-w-0">
            <TrendingUp className="w-3.5 h-3.5 shrink-0" />
            <div>
              <p className="font-medium">Margine atteso</p>
              <p className="font-bold text-sm">
                {pct(rec.expected_margin_pct)}{' '}
                <span className="font-normal text-green-700">
                  ({eur(rec.expected_margin_eur)} × {rec.qty} pz)
                </span>
              </p>
            </div>
          </div>
        </div>

        {/* Data sufficiency badge */}
        <div className="flex items-center gap-2">
          <span className={cn('inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full', sc.color)}>
            <span className={cn('w-1.5 h-1.5 rounded-full', sc.dot)} />
            {sc.label}
          </span>
          <span className="text-xs text-gray-400">
            Pool: {rec.explanation_trace.find(t => t.used)?.pool_size ?? 0} offerte
          </span>
        </div>

        {/* Expandable trace */}
        <ExplanationTrace trace={rec.explanation_trace} />
      </div>
    </div>
  )
}
