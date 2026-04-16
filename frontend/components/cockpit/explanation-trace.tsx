'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, CheckCircle2, Circle } from 'lucide-react'
import { type ExplanationStep } from '@/lib/api'
import { pct, cn } from '@/lib/utils'

const STEP_LABELS: Record<string, string> = {
  cliente_articolo: 'Cliente × Articolo',
  cliente_sco:      'Cliente × Famiglia (SCO)',
  tipo_articolo:    'Tipo cliente × Articolo',
  tipo_sco:         'Tipo cliente × Famiglia',
  provincia_sco:    'Provincia × Famiglia',
  agente_sco:       'Agente × Famiglia',
  sco_globale:      'Famiglia (globale)',
  promo_attiva:     'Promozione attiva',
}

interface Props {
  trace: ExplanationStep[]
}

export function ExplanationTrace({ trace }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="border-t border-gray-100 pt-3 mt-3">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors"
      >
        {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        Traccia ragionamento ({trace.filter(t => t.step !== 'promo_attiva').length} step)
      </button>

      {open && (
        <ol className="mt-3 space-y-1.5 animate-fade-in">
          {trace.map((step, i) => (
            <li key={i} className={cn(
              'flex items-start gap-2 text-xs rounded-lg px-2.5 py-2',
              step.used
                ? 'bg-blue-50 text-blue-900'
                : step.step === 'promo_attiva'
                  ? 'bg-amber-50 text-amber-800'
                  : 'text-gray-500'
            )}>
              {step.used ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-500 mt-0.5 shrink-0" />
              ) : (
                <Circle className="w-3.5 h-3.5 mt-0.5 shrink-0 opacity-40" />
              )}
              <div className="flex-1">
                <span className="font-medium">
                  {STEP_LABELS[step.step] ?? step.step}
                </span>
                {step.step !== 'promo_attiva' && (
                  <span className="ml-1.5 opacity-70">
                    {step.pool_size} offerte
                    {step.median_discount != null
                      ? ` · mediana ${pct(step.median_discount)}`
                      : ''}
                  </span>
                )}
                {step.detail && (
                  <p className="mt-0.5 opacity-80">{step.detail}</p>
                )}
              </div>
              {step.used && (
                <span className="shrink-0 text-blue-600 font-semibold">← usato</span>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
