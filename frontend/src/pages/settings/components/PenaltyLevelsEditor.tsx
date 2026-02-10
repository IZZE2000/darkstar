import React from 'react'
import { NumberInput } from '../../../components/ui/NumberInput'

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
                                        <span className="text-[10px] uppercase text-text/60 font-bold mb-0.5">
                                            {isLast ? 'Range' : 'Limit %'}
                                        </span>
                                        <div className="flex items-center">
                                            <div className="w-21">
                                                <NumberInput
                                                    value={level.max_soc}
                                                    onChange={(val) =>
                                                        updateLevel(tier.key, {
                                                            max_soc: Math.min(
                                                                100,
                                                                Math.max(startSoc, parseInt(val) || 0),
                                                            ),
                                                        })
                                                    }
                                                    disabled={disabled}
                                                    className="h-8 text-sm font-mono font-bold text-center"
                                                />
                                            </div>
                                            <span className="text-[10px] text-muted/40 font-bold ml-1.5">%</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Value Input */}
                                <div className="relative group flex items-center gap-2">
                                    <div className="w-32">
                                        <NumberInput
                                            value={level.penalty_sek}
                                            onChange={(val) =>
                                                updateLevel(tier.key, { penalty_sek: parseFloat(val) || 0 })
                                            }
                                            step={0.01}
                                            min={0}
                                            disabled={disabled}
                                            className="font-bold font-mono text-right"
                                        />
                                    </div>
                                    <span className="text-[10px] text-muted/60 font-bold pointer-events-none whitespace-nowrap">
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
