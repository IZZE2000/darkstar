import { ArrowRight, Gauge } from 'lucide-react'
import Card from './Card'
import { type PlannerSIndex, type PriceOutlookResponse } from '../lib/api'

type PlannerMeta = {
    planned_at?: string
    planner_version?: string
    s_index?: PlannerSIndex
} | null

interface BatteryStrategyCardProps {
    soc: number | null
    socTarget: number
    batteryCapacity: number
    plannerMeta: PlannerMeta
    batteryCycles: number | null
    priceOutlook: PriceOutlookResponse | undefined
}

export default function BatteryStrategyCard({
    soc,
    socTarget,
    batteryCapacity,
    plannerMeta,
    batteryCycles,
    priceOutlook,
}: BatteryStrategyCardProps) {
    const hasPriceData = priceOutlook && priceOutlook.days.length > 0

    return (
        <Card className="p-4 flex flex-col h-full bg-surface">
            {/* Card Header */}
            <div className="flex items-center gap-2 mb-4">
                <div className="p-1.5 rounded-lg bg-ai/10 text-ai">
                    <Gauge className="h-4 w-4" />
                </div>
                <span className="text-sm font-medium text-text">Battery & Strategy</span>
            </div>

            {/* Battery SoC + Target */}
            <div className="mb-5 flex flex-col gap-1.5">
                <div className="flex items-center gap-3 text-5xl font-bold leading-none">
                    <span className={`${(soc ?? 0) > 50 ? 'text-good' : (soc ?? 0) > 20 ? 'text-warn' : 'text-bad'}`}>
                        {soc?.toFixed(0) ?? '—'}%
                    </span>
                    <ArrowRight className="w-10 h-10 text-muted" strokeWidth={3} />
                    <span className="text-text">{socTarget?.toFixed(0) ?? '—'}%</span>
                </div>
                {batteryCapacity > 0 && (
                    <div className="text-[11px] text-muted">
                        {soc != null ? ((soc / 100) * batteryCapacity).toFixed(1) : '—'} of {batteryCapacity.toFixed(1)}{' '}
                        kWh
                    </div>
                )}
            </div>

            {/* Strategy Metrics — 2×2 relaxed grid */}
            <div className="grid grid-cols-2 gap-y-4 gap-x-3 mb-5 pb-5 border-b border-line/30">
                <div>
                    <div className="text-[9px] text-muted uppercase tracking-wider mb-1">S-Index</div>
                    <div className="text-base font-semibold text-text">
                        {plannerMeta?.s_index?.effective_load_margin || plannerMeta?.s_index?.risk_factor
                            ? `x${(plannerMeta.s_index.effective_load_margin ?? plannerMeta.s_index.risk_factor ?? 1).toFixed(2)}`
                            : '—'}
                    </div>
                </div>
                <div>
                    <div className="text-[9px] text-muted uppercase tracking-wider mb-1">Cycles</div>
                    <div className="text-base font-semibold text-text">{batteryCycles?.toFixed(1) ?? '—'}</div>
                </div>
                {(() => {
                    const safetyFloor = plannerMeta?.s_index?.safety_floor?.calculated_floor_kwh
                    const tradableKwh =
                        safetyFloor != null && batteryCapacity && batteryCapacity > 0
                            ? Math.max(0, batteryCapacity - safetyFloor)
                            : null
                    return (
                        <>
                            <div>
                                <div className="text-[9px] text-muted uppercase tracking-wider mb-1">Safety Floor</div>
                                <div className="text-base font-semibold text-text">
                                    {safetyFloor != null ? `${safetyFloor.toFixed(1)} kWh` : '—'}
                                </div>
                            </div>
                            <div>
                                <div className="text-[9px] text-muted uppercase tracking-wider mb-1">Tradable</div>
                                <div className="text-base font-semibold text-text">
                                    {tradableKwh != null ? `${tradableKwh.toFixed(1)} kWh` : '—'}
                                </div>
                            </div>
                        </>
                    )
                })()}
            </div>

            {/* Price Outlook — full-width horizontal bars */}
            {hasPriceData && (
                <div className="mt-auto">
                    <div className="text-[9px] text-muted uppercase tracking-wider mb-2">7-Day Price Outlook</div>
                    <div className="space-y-1">
                        {priceOutlook.days.slice(0, 7).map((day) => {
                            const barColor =
                                {
                                    cheap: 'bg-green-500/80',
                                    normal: 'bg-amber-500/80',
                                    expensive: 'bg-red-500/80',
                                    unknown: 'bg-gray-500/50',
                                }[day.level] || 'bg-gray-500/50'
                            const pct = Math.min(100, Math.max(5, (day.avg_spot_p50 / 2) * 100))
                            const opacityMap = { high: 1, medium: 0.7, low: 0.4 }
                            const opacity = opacityMap[day.confidence as keyof typeof opacityMap] || 0.5
                            return (
                                <div key={day.date} className="flex items-center gap-2 group">
                                    <span className="text-[10px] text-text w-7 text-right font-medium">
                                        {day.day_label.slice(0, 3)}
                                    </span>
                                    <div className="flex-1 h-4 bg-surface2 rounded-sm overflow-hidden relative">
                                        <div
                                            className={`h-full rounded-sm ${barColor} transition-all`}
                                            style={{ width: `${pct}%`, opacity }}
                                        />
                                    </div>
                                    <span className="text-[10px] text-muted w-14 text-right tabular-nums">
                                        {day.avg_spot_p50.toFixed(2)}
                                    </span>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}
            {!hasPriceData && (
                <div className="flex-1 flex items-center justify-center text-[11px] text-muted">
                    Price data loading...
                </div>
            )}
        </Card>
    )
}
