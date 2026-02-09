import React from 'react'
import { Info } from 'lucide-react'

interface PenaltyLevel {
    name: string
    min_soc: number
    max_soc: number
    penalty_sek: number
}

interface PenaltyLevelsEditorProps {
    value: PenaltyLevel[] | string // Handle JSON string from FormState if needed, but utils should parse it
    onChange: (value: PenaltyLevel[]) => void
    disabled?: boolean
}

const TIERS = [
    { key: 'emergency', label: 'Emergency', helper: 'Urgent charging: highest priority' },
    { key: 'high', label: 'High Priority', helper: 'Prefer charging soon' },
    { key: 'normal', label: 'Normal', helper: 'Standard smart charging' },
    { key: 'opportunistic', label: 'Opportunistic', helper: 'Only if very cheap' },
]

export const PenaltyLevelsEditor: React.FC<PenaltyLevelsEditorProps> = ({ value, onChange, disabled }) => {
    // Parse if it's a string (though utils should handle this, defensive)
    const currentLevels: PenaltyLevel[] = Array.isArray(value)
        ? value
        : typeof value === 'string' && value.trim()
          ? JSON.parse(value)
          : []

    // Ensure we have all 4 tiers present for the UI
    const safeValue = TIERS.map((tier) => {
        const existing = currentLevels.find((v) => v.name === tier.key)
        return existing || { name: tier.key, min_soc: 0, max_soc: 100, penalty_sek: 0 }
    })

    const updateLevel = (name: string, updates: Partial<PenaltyLevel>) => {
        const newValue = safeValue.map((v) => (v.name === name ? { ...v, ...updates } : v))
        onChange(newValue)
    }

    return (
        <div className="space-y-4 col-span-2">
            <div className="grid grid-cols-1 gap-2.5">
                {TIERS.map((tier) => {
                    const level = safeValue.find((v) => v.name === tier.key)!
                    return (
                        <div
                            key={tier.key}
                            className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 bg-surface-elevated rounded-xl border border-line/40 hover:border-line/60 transition-all gap-4"
                        >
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="text-sm font-bold text-text uppercase tracking-tight">
                                        {tier.label}
                                    </span>
                                    {tier.key === 'emergency' && (
                                        <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-bad/10 text-bad font-black uppercase tracking-widest ring-1 ring-bad/20">
                                            Urgent
                                        </span>
                                    )}
                                </div>
                                <p className="text-[11px] text-muted leading-snug">{tier.helper}</p>
                            </div>

                            <div className="flex items-center gap-4 self-end sm:self-auto">
                                {/* SoC Range Display/Inputs */}
                                <div className="flex items-center gap-1.5 bg-surface2/40 px-2.5 py-1.5 rounded-lg border border-line/20">
                                    <div className="flex flex-col items-center">
                                        <span className="text-[8px] uppercase text-muted/60 font-bold mb-0.5">
                                            Min %
                                        </span>
                                        <input
                                            type="number"
                                            value={level.min_soc}
                                            disabled={disabled}
                                            onChange={(e) =>
                                                updateLevel(tier.key, { min_soc: parseInt(e.target.value) || 0 })
                                            }
                                            className="w-10 bg-transparent text-center text-xs font-mono font-bold text-muted focus:outline-none focus:text-accent transition-colors"
                                        />
                                    </div>
                                    <span className="text-muted/20 pb-2 text-xs">─</span>
                                    <div className="flex flex-col items-center">
                                        <span className="text-[8px] uppercase text-muted/60 font-bold mb-0.5">
                                            Max %
                                        </span>
                                        <input
                                            type="number"
                                            value={level.max_soc}
                                            disabled={disabled}
                                            onChange={(e) =>
                                                updateLevel(tier.key, { max_soc: parseInt(e.target.value) || 0 })
                                            }
                                            className="w-10 bg-transparent text-center text-xs font-mono font-bold text-muted focus:outline-none focus:text-accent transition-colors"
                                        />
                                    </div>
                                </div>

                                {/* Penalty Input */}
                                <div className="relative group">
                                    <input
                                        type="number"
                                        step="0.1"
                                        min="0"
                                        value={level.penalty_sek}
                                        onChange={(e) =>
                                            updateLevel(tier.key, { penalty_sek: parseFloat(e.target.value) || 0 })
                                        }
                                        disabled={disabled}
                                        className="w-28 rounded-lg border border-line/40 bg-surface2 pr-10 pl-3 py-2.5 text-sm text-text font-bold font-mono focus:border-ai focus:ring-1 focus:ring-ai/20 focus:outline-none transition-all text-right group-hover:border-line/80 shadow-sm"
                                    />
                                    <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-muted/60 font-bold pointer-events-none mt-0.5">
                                        SEK
                                    </span>
                                </div>
                            </div>
                        </div>
                    )
                })}
            </div>

            <div className="flex items-start gap-3 p-4 bg-ai/5 border border-ai/20 rounded-2xl">
                <div className="p-2 bg-ai/10 rounded-lg shrink-0">
                    <Info size={16} className="text-ai" />
                </div>
                <div className="space-y-1">
                    <p className="text-xs font-bold text-ai/80 uppercase tracking-wider">Penalty Strategy</p>
                    <p className="text-[11px] text-muted leading-relaxed">
                        Penalties are added to the price during optimization.
                        <span className="text-text/80 mx-1 border-b border-dotted border-muted/50 pb-0.5">
                            High values (e.g. 10.0 SEK)
                        </span>{' '}
                        force immediate charging.
                        <span className="text-text/80 mx-1 border-b border-dotted border-muted/50 pb-0.5">
                            Low values (0.1 SEK)
                        </span>{' '}
                        prioritize only the cheapest hours.
                    </p>
                </div>
            </div>
        </div>
    )
}
