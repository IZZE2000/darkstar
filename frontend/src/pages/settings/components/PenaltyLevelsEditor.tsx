import React from 'react'

interface PenaltyLevel {
    name: string
    max_soc: number
    penalty_sek: number
}

interface PenaltyLevelsEditorProps {
    value: PenaltyLevel[] | string
    onChange: (value: PenaltyLevel[]) => void
    disabled?: boolean
}

const TIERS = [
    { key: 'emergency', label: 'Critical Charge', helper: 'Charge ASAP: pay any price within limit' },
    { key: 'high', label: 'Priority', helper: 'Prefer charging soon' },
    { key: 'normal', label: 'Balanced', helper: 'Standard smart charging' },
    { key: 'opportunistic', label: 'Low Price Only', helper: 'Only if extremely cheap' },
]

export const PenaltyLevelsEditor: React.FC<PenaltyLevelsEditorProps> = ({ value, onChange, disabled }) => {
    // Parse if it's a string
    const currentLevels: PenaltyLevel[] = Array.isArray(value)
        ? value
        : typeof value === 'string' && value.trim()
          ? JSON.parse(value)
          : []

    // Ensure we have all 4 tiers present for the UI
    const safeValue = TIERS.map((tier) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const existing = currentLevels.find((v) => v.name === tier.key) as any
        return {
            name: tier.key,
            max_soc: existing?.max_soc ?? 100,
            penalty_sek: existing?.penalty_sek ?? 0,
        }
    })

    const updateLevel = (name: string, updates: Partial<PenaltyLevel>) => {
        const newValue = safeValue.map((v) => (v.name === name ? { ...v, ...updates } : v))
        onChange(newValue)
    }

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-1 gap-2.5">
                {TIERS.map((tier, index) => {
                    const level = safeValue.find((v) => v.name === tier.key)!
                    const prevLevel = index > 0 ? safeValue[index - 1] : null
                    const startSoc = prevLevel ? prevLevel.max_soc : 0
                    const isLast = index === TIERS.length - 1

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
                                            High Priority
                                        </span>
                                    )}
                                </div>
                                <p className="text-[11px] text-muted leading-snug">{tier.helper}</p>
                            </div>

                            <div className="flex items-center gap-4 self-end sm:self-auto">
                                {/* Chained SoC Range Display */}
                                <div className="flex items-center gap-1.5 bg-surface2/40 px-3 py-2 rounded-lg border border-line/20">
                                    <div className="flex flex-col items-center">
                                        <span className="text-[8px] uppercase text-text/40 font-bold mb-0.5">
                                            {isLast ? 'Range' : 'Limit %'}
                                        </span>
                                        {isLast ? (
                                            <span className="text-xs font-mono font-bold text-muted/60 px-2">100%</span>
                                        ) : (
                                            <div className="flex items-center">
                                                <input
                                                    type="number"
                                                    value={level.max_soc}
                                                    disabled={disabled}
                                                    onChange={(e) =>
                                                        updateLevel(tier.key, {
                                                            max_soc: Math.min(
                                                                100,
                                                                Math.max(startSoc, parseInt(e.target.value) || 0),
                                                            ),
                                                        })
                                                    }
                                                    className="w-10 bg-transparent text-center text-xs font-mono font-bold text-accent focus:outline-none focus:ring-0 transition-colors"
                                                />
                                                <span className="text-[10px] text-muted/40 font-bold ml-0.5">%</span>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Value Input */}
                                <div className="relative group">
                                    <input
                                        type="number"
                                        step="0.01"
                                        min="0"
                                        value={level.penalty_sek}
                                        onChange={(e) =>
                                            updateLevel(tier.key, { penalty_sek: parseFloat(e.target.value) || 0 })
                                        }
                                        disabled={disabled}
                                        className="w-28 rounded-lg border border-line/40 bg-surface2 pr-14 pl-3 py-2.5 text-sm text-text font-bold font-mono focus:border-ai focus:ring-1 focus:ring-ai/20 focus:outline-none transition-all text-right group-hover:border-line/80 shadow-sm"
                                    />
                                    <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-muted/60 font-bold pointer-events-none mt-0.5">
                                        SEK/kWh
                                    </span>
                                </div>
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
