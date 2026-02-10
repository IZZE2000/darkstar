import React, { useState } from 'react'
import { Plus, Minus, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import AzimuthDial from '../../../components/AzimuthDial'
import TiltDial from '../../../components/TiltDial'
import { Badge } from '../../../components/ui/Badge'
import { NumberInput } from '../../../components/ui/NumberInput'

interface SolarArray {
    name: string
    azimuth: number
    tilt: number
    kwp: number
}

interface SolarArraysEditorProps {
    arrays: SolarArray[]
    onChange: (arrays: SolarArray[]) => void
    disabled?: boolean
}

export const SolarArraysEditor: React.FC<SolarArraysEditorProps> = ({ arrays, onChange, disabled }) => {
    const [expandedIndex, setExpandedIndex] = useState<number | null>(0)

    const totalKwp = arrays.reduce((sum, a) => sum + (Number(a.kwp) || 0), 0)

    const addArray = () => {
        if (arrays.length >= 6) return
        const newArray: SolarArray = {
            name: `Array ${arrays.length + 1}`,
            azimuth: 180,
            tilt: 35,
            kwp: 5.0,
        }
        const newArrays = [...arrays, newArray]
        onChange(newArrays)
        setExpandedIndex(newArrays.length - 1)
    }

    const removeArray = (index: number) => {
        if (arrays.length <= 1) return
        const newArrays = arrays.filter((_, i) => i !== index)
        onChange(newArrays)
        if (expandedIndex === index) {
            setExpandedIndex(null)
        } else if (expandedIndex !== null && expandedIndex > index) {
            setExpandedIndex(expandedIndex - 1)
        }
    }

    const updateArray = (index: number, updates: Partial<SolarArray>) => {
        const newArrays = arrays.map((a, i) => (i === index ? { ...a, ...updates } : a))
        onChange(newArrays)
    }

    return (
        <div className="space-y-4 col-span-2">
            <div className="flex items-center justify-between bg-surface-elevated p-3 rounded-xl border border-line/40">
                <div className="flex items-center gap-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-muted">Solar Arrays</span>
                    <Badge variant={totalKwp > 500 ? 'warning' : 'info'}>Total: {totalKwp.toFixed(1)} kWp</Badge>
                </div>
                {!disabled && (
                    <div className="flex items-center gap-2">
                        <button
                            type="button"
                            onClick={() => arrays.length > 1 && removeArray(arrays.length - 1)}
                            disabled={arrays.length <= 1}
                            className="p-1.5 rounded-lg bg-surface2 hover:bg-bad/20 hover:text-bad border border-line/50 transition-colors disabled:opacity-30"
                        >
                            <Minus size={16} />
                        </button>
                        <button
                            type="button"
                            onClick={addArray}
                            disabled={arrays.length >= 6}
                            className="p-1.5 rounded-lg bg-surface2 hover:bg-good/20 hover:text-good border border-line/50 transition-colors disabled:opacity-30"
                        >
                            <Plus size={16} />
                        </button>
                    </div>
                )}
            </div>

            <div className="space-y-4 overflow-visible pb-4">
                {arrays.map((array, index) => (
                    <div
                        key={index}
                        className="overflow-visible border border-line/40 rounded-xl bg-surface-elevated mb-2"
                    >
                        <button
                            type="button"
                            onClick={() => setExpandedIndex(expandedIndex === index ? null : index)}
                            className="w-full flex items-center justify-between p-3 hover:bg-surface2 transition-colors text-left rounded-xl"
                        >
                            <div className="flex items-center gap-3">
                                <div className="w-6 h-6 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center text-[10px] font-bold text-accent">
                                    {index + 1}
                                </div>
                                <div>
                                    <div className="text-sm font-semibold">{array.name || `Array ${index + 1}`}</div>
                                    <div className="text-[10px] text-muted uppercase tracking-tight">
                                        {array.kwp} kWp · {array.azimuth}° Azimuth · {array.tilt}° Tilt
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                {!disabled && arrays.length > 1 && (
                                    <button
                                        type="button"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            removeArray(index)
                                        }}
                                        className="p-1.5 rounded-lg text-muted hover:text-bad hover:bg-bad/10 transition-colors"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                )}
                                {expandedIndex === index ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </div>
                        </button>

                        <AnimatePresence initial={false}>
                            {expandedIndex === index && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="overflow-visible"
                                >
                                    <div className="p-4 border-t border-line/10 grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div className="sm:col-span-2">
                                            <label className="text-[10px] uppercase font-bold text-muted mb-1.5 block">
                                                Array Name
                                            </label>
                                            <input
                                                type="text"
                                                value={array.name}
                                                onChange={(e) => updateArray(index, { name: e.target.value })}
                                                disabled={disabled}
                                                placeholder={`e.g. Roof South`}
                                                className="w-full rounded-lg border border-line/50 bg-surface2 px-3 py-2 text-sm text-text focus:border-accent focus:outline-none disabled:opacity-50"
                                            />
                                        </div>

                                        <div className="space-y-3">
                                            <label className="text-[10px] uppercase font-bold text-muted block">
                                                Orientation
                                            </label>
                                            <div className="space-y-4">
                                                <div>
                                                    <span className="text-[9px] text-muted mb-1 block">
                                                        Azimuth (Dial)
                                                    </span>
                                                    <AzimuthDial
                                                        value={array.azimuth}
                                                        onChange={(val) => updateArray(index, { azimuth: val })}
                                                    />
                                                    <NumberInput
                                                        value={array.azimuth}
                                                        onChange={(val) => updateArray(index, { azimuth: Number(val) })}
                                                        disabled={disabled}
                                                        step={1}
                                                    />
                                                </div>
                                                <div>
                                                    <span className="text-[9px] text-muted mb-1 block">
                                                        Tilt (Dial)
                                                    </span>
                                                    <TiltDial
                                                        value={array.tilt}
                                                        onChange={(val) => updateArray(index, { tilt: val })}
                                                    />
                                                    <NumberInput
                                                        value={array.tilt}
                                                        onChange={(val) => updateArray(index, { tilt: Number(val) })}
                                                        disabled={disabled}
                                                        step={1}
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        <div className="space-y-3">
                                            <label className="text-[10px] uppercase font-bold text-muted block">
                                                Capacity
                                            </label>
                                            <div className="mt-1">
                                                <span className="text-[9px] text-muted mb-1 block">
                                                    Peak Power (kWp)
                                                </span>
                                                <NumberInput
                                                    value={array.kwp}
                                                    onChange={(val) => updateArray(index, { kwp: Number(val) })}
                                                    disabled={disabled}
                                                    step={0.1}
                                                />
                                                {array.kwp > 50 && (
                                                    <p className="text-[10px] text-bad mt-1">
                                                        ⚠️ Individual array limit is 50 kWp
                                                    </p>
                                                )}
                                            </div>
                                            <div className="p-3 bg-surface2 rounded-xl border border-line/10 text-[11px] text-muted leading-relaxed">
                                                <p className="font-semibold text-text mb-1">Scaling Note</p>
                                                This array accounts for {((array.kwp / totalKwp) * 100 || 0).toFixed(0)}
                                                % of total system production.
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                ))}
            </div>

            {totalKwp > 500 && (
                <div className="p-3 bg-bad/10 border border-bad/30 rounded-xl text-xs text-bad flex items-start gap-2">
                    <span className="text-base leading-none mt-0.5">⚠️</span>
                    <div>
                        <strong>Total capacity limit exceeded (500 kWp).</strong>
                        <p className="mt-1 opacity-80">
                            Solar forecasting and strategy may be inaccurate or rejected by the backend.
                        </p>
                    </div>
                </div>
            )}
        </div>
    )
}
