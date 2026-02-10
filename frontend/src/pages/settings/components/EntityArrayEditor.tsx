import React, { useState } from 'react'
import { Plus, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Badge } from '../../../components/ui/Badge'
import Switch from '../../../components/ui/Switch'
import EntitySelect from '../../../components/EntitySelect'
import { HaEntity } from '../types'

// Water Heater Entity Type
export interface WaterHeaterEntity {
    id: string
    name: string
    enabled: boolean
    power_kw: number
    min_kwh_per_day: number
    max_hours_between_heating: number
    water_min_spacing_hours: number
    sensor: string
    type: 'binary' | 'modulating'
    nominal_power_kw: number
}

// EV Charger Entity Type
export interface EVChargerEntity {
    id: string
    name: string
    enabled: boolean
    max_power_kw: number
    battery_capacity_kwh: number
    min_soc_percent: number
    target_soc_percent: number
    sensor: string
    type: 'variable' | 'constant'
    nominal_power_kw: number
    penalty_levels?: Array<{ max_soc: number; penalty_sek: number }>
}

type EntityType = 'water_heater' | 'ev_charger'

interface EntityArrayEditorProps {
    entities: WaterHeaterEntity[] | EVChargerEntity[]
    entityType: EntityType
    onChange: (entities: WaterHeaterEntity[] | EVChargerEntity[]) => void
    disabled?: boolean
    haEntities?: HaEntity[]
    haLoading?: boolean
}

const createDefaultWaterHeater = (index: number): WaterHeaterEntity => ({
    id: `water_heater_${index + 1}`,
    name: `Water Heater ${index + 1}`,
    enabled: true,
    power_kw: 3.0,
    min_kwh_per_day: 6.0,
    max_hours_between_heating: 8,
    water_min_spacing_hours: 4,
    sensor: '',
    type: 'binary',
    nominal_power_kw: 3.0,
})

const createDefaultEVCharger = (index: number): EVChargerEntity => ({
    id: `ev_charger_${index + 1}`,
    name: `EV Charger ${index + 1}`,
    enabled: true,
    max_power_kw: 11.0,
    battery_capacity_kwh: 82.0,
    min_soc_percent: 20.0,
    target_soc_percent: 80.0,
    sensor: '',
    type: 'variable',
    nominal_power_kw: 11.0,
    penalty_levels: [
        { max_soc: 50, penalty_sek: 0.5 },
        { max_soc: 80, penalty_sek: 0.2 },
        { max_soc: 100, penalty_sek: 0.0 },
    ],
})

export const EntityArrayEditor: React.FC<EntityArrayEditorProps> = ({
    entities,
    entityType,
    onChange,
    disabled = false,
    haEntities = [],
    haLoading = false,
}) => {
    const [expandedIndex, setExpandedIndex] = useState<number | null>(entities.length > 0 ? 0 : null)

    const isWaterHeater = entityType === 'water_heater'
    const maxEntities = isWaterHeater ? 4 : 3
    const title = isWaterHeater ? 'Water Heaters' : 'EV Chargers'

    const addEntity = () => {
        if (entities.length >= maxEntities) return
        const newEntity = isWaterHeater
            ? createDefaultWaterHeater(entities.length)
            : createDefaultEVCharger(entities.length)
        const newEntities = [...entities, newEntity]
        onChange(newEntities)
        setExpandedIndex(newEntities.length - 1)
    }

    const removeEntity = (index: number) => {
        const newEntities = entities.filter((_, i) => i !== index)
        onChange(newEntities)
        if (expandedIndex === index) {
            setExpandedIndex(null)
        } else if (expandedIndex !== null && expandedIndex > index) {
            setExpandedIndex(expandedIndex - 1)
        }
    }

    const updateEntity = (index: number, updates: Partial<WaterHeaterEntity | EVChargerEntity>) => {
        const newEntities = entities.map((e, i) => (i === index ? { ...e, ...updates } : e))
        onChange(newEntities)
    }

    const toggleEnabled = (index: number) => {
        const entity = entities[index]
        updateEntity(index, { enabled: !entity.enabled } as Partial<WaterHeaterEntity | EVChargerEntity>)
    }

    const totalPower = entities.reduce(
        (sum, e) =>
            sum +
            (Number(
                e.enabled
                    ? isWaterHeater
                        ? (e as WaterHeaterEntity).power_kw
                        : (e as EVChargerEntity).max_power_kw
                    : 0,
            ) || 0),
        0,
    )
    const enabledCount = entities.filter((e) => e.enabled).length

    return (
        <div className="space-y-4 col-span-2">
            <div className="flex items-center justify-between bg-surface-elevated p-3 rounded-xl border border-line/40">
                <div className="flex items-center gap-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-muted">{title}</span>
                    <Badge variant={enabledCount === 0 ? 'warning' : 'info'}>
                        {enabledCount} / {entities.length} enabled · {totalPower.toFixed(1)} kW total
                    </Badge>
                </div>
                {!disabled && (
                    <button
                        type="button"
                        onClick={addEntity}
                        disabled={entities.length >= maxEntities}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface2 hover:bg-good/20 hover:text-good border border-line/50 transition-colors disabled:opacity-30 text-xs font-semibold"
                    >
                        <Plus size={14} />
                        Add {isWaterHeater ? 'Heater' : 'Charger'}
                    </button>
                )}
            </div>

            <div className="space-y-3 overflow-visible pb-4">
                {entities.length === 0 && (
                    <div className="text-center py-8 px-4 bg-surface-elevated rounded-xl border border-line/20 border-dashed">
                        <div className="text-muted text-sm mb-2">No {title.toLowerCase()} configured</div>
                        <button
                            type="button"
                            onClick={addEntity}
                            disabled={disabled}
                            className="text-accent text-xs font-semibold hover:underline disabled:opacity-50"
                        >
                            + Add your first {isWaterHeater ? 'water heater' : 'EV charger'}
                        </button>
                    </div>
                )}

                {entities.map((entity, index) => (
                    <div
                        key={entity.id || index}
                        className={`overflow-visible border rounded-xl bg-surface-elevated mb-2 transition-all duration-200 ${
                            entity.enabled ? 'border-line/40' : 'border-line/20 opacity-75'
                        }`}
                    >
                        <button
                            type="button"
                            onClick={() => setExpandedIndex(expandedIndex === index ? null : index)}
                            className="w-full flex items-center justify-between p-3 hover:bg-surface2 transition-colors text-left rounded-xl"
                        >
                            <div className="flex items-center gap-3">
                                <div
                                    className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                                        entity.enabled
                                            ? 'bg-accent/10 border border-accent/20 text-accent'
                                            : 'bg-surface2 border border-line/30 text-muted'
                                    }`}
                                >
                                    {index + 1}
                                </div>
                                <div>
                                    <div className="text-sm font-semibold flex items-center gap-2">
                                        {entity.name || `${isWaterHeater ? 'Water Heater' : 'EV Charger'} ${index + 1}`}
                                        {!entity.enabled && (
                                            <span className="text-[10px] px-1.5 py-0.5 bg-surface2 text-muted rounded-full">
                                                Disabled
                                            </span>
                                        )}
                                    </div>
                                    <div className="text-[10px] text-muted uppercase tracking-tight">
                                        {isWaterHeater
                                            ? `${(entity as WaterHeaterEntity).power_kw} kW · ${(entity as WaterHeaterEntity).min_kwh_per_day} kWh/day · ${(entity as WaterHeaterEntity).sensor || 'No sensor'}`
                                            : `${(entity as EVChargerEntity).max_power_kw} kW max · ${(entity as EVChargerEntity).battery_capacity_kwh} kWh battery · ${entity.sensor || 'No sensor'}`}
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                {!disabled && (
                                    <>
                                        <Switch
                                            checked={entity.enabled}
                                            onCheckedChange={() => toggleEnabled(index)}
                                            onClick={(e) => e.stopPropagation()}
                                        />
                                        <button
                                            type="button"
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                removeEntity(index)
                                            }}
                                            className="p-1.5 rounded-lg text-muted hover:text-bad hover:bg-bad/10 transition-colors ml-2"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </>
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
                                        {/* ID Field - Read Only */}
                                        <div>
                                            <label className="text-[10px] uppercase font-bold text-muted mb-1.5 block">
                                                ID (Read-only)
                                            </label>
                                            <input
                                                type="text"
                                                value={entity.id}
                                                disabled
                                                className="w-full rounded-lg border border-line/30 bg-surface2/50 px-3 py-2 text-sm text-muted cursor-not-allowed"
                                            />
                                            <p className="text-[10px] text-muted mt-1">
                                                Unique identifier used internally
                                            </p>
                                        </div>

                                        {/* Name Field */}
                                        <div>
                                            <label className="text-[10px] uppercase font-bold text-muted mb-1.5 block">
                                                Display Name *
                                            </label>
                                            <input
                                                type="text"
                                                value={entity.name}
                                                onChange={(e) => updateEntity(index, { name: e.target.value })}
                                                disabled={disabled}
                                                placeholder={`e.g. Main ${isWaterHeater ? 'Tank' : 'Charger'}`}
                                                className="w-full rounded-lg border border-line/50 bg-surface2 px-3 py-2 text-sm text-text focus:border-accent focus:outline-none disabled:opacity-50"
                                            />
                                        </div>

                                        {/* Power Rating */}
                                        <div>
                                            <label className="text-[10px] uppercase font-bold text-muted mb-1.5 block">
                                                {isWaterHeater ? 'Power Rating' : 'Max Charging Power'} (kW) *
                                            </label>
                                            <input
                                                type="number"
                                                step="0.1"
                                                min="0"
                                                value={
                                                    isWaterHeater
                                                        ? (entity as WaterHeaterEntity).power_kw
                                                        : (entity as EVChargerEntity).max_power_kw
                                                }
                                                onChange={(e) =>
                                                    updateEntity(index, {
                                                        [isWaterHeater ? 'power_kw' : 'max_power_kw']: Number(
                                                            e.target.value,
                                                        ),
                                                    } as Partial<WaterHeaterEntity | EVChargerEntity>)
                                                }
                                                disabled={disabled}
                                                className="w-full rounded-lg border border-line/50 bg-surface2 px-3 py-2 text-sm text-text focus:border-accent focus:outline-none disabled:opacity-50"
                                            />
                                        </div>

                                        {/* Daily Energy / Battery Capacity */}
                                        <div>
                                            <label className="text-[10px] uppercase font-bold text-muted mb-1.5 block">
                                                {isWaterHeater ? 'Daily Energy Requirement' : 'Battery Capacity'} (kWh)
                                            </label>
                                            <input
                                                type="number"
                                                step="0.1"
                                                min="0"
                                                value={
                                                    isWaterHeater
                                                        ? (entity as WaterHeaterEntity).min_kwh_per_day
                                                        : (entity as EVChargerEntity).battery_capacity_kwh
                                                }
                                                onChange={(e) =>
                                                    updateEntity(index, {
                                                        [isWaterHeater ? 'min_kwh_per_day' : 'battery_capacity_kwh']:
                                                            Number(e.target.value),
                                                    } as Partial<WaterHeaterEntity | EVChargerEntity>)
                                                }
                                                disabled={disabled}
                                                className="w-full rounded-lg border border-line/50 bg-surface2 px-3 py-2 text-sm text-text focus:border-accent focus:outline-none disabled:opacity-50"
                                            />
                                        </div>

                                        {/* Entity Sensor */}
                                        <div className="sm:col-span-2">
                                            <label className="text-[10px] uppercase font-bold text-muted mb-1.5 block">
                                                Power Sensor (HA Entity) *
                                            </label>
                                            <EntitySelect
                                                entities={haEntities}
                                                value={entity.sensor}
                                                onChange={(val) => updateEntity(index, { sensor: val })}
                                                loading={haLoading}
                                                placeholder="Select Home Assistant power sensor..."
                                                disabled={disabled}
                                            />
                                            <p className="text-[10px] text-muted mt-1">
                                                Used for load disaggregation and real-time monitoring
                                            </p>
                                        </div>

                                        {/* Type Selection */}
                                        <div>
                                            <label className="text-[10px] uppercase font-bold text-muted mb-1.5 block">
                                                Load Type
                                            </label>
                                            <select
                                                value={entity.type}
                                                onChange={(e) =>
                                                    updateEntity(index, {
                                                        type: e.target.value as
                                                            | 'binary'
                                                            | 'modulating'
                                                            | 'variable'
                                                            | 'constant',
                                                    })
                                                }
                                                disabled={disabled}
                                                className="w-full rounded-lg border border-line/50 bg-surface2 px-3 py-2 text-sm text-text focus:border-accent focus:outline-none disabled:opacity-50"
                                            >
                                                {isWaterHeater ? (
                                                    <>
                                                        <option value="binary">Binary (On/Off)</option>
                                                        <option value="modulating">Modulating</option>
                                                    </>
                                                ) : (
                                                    <>
                                                        <option value="variable">Variable (EV)</option>
                                                        <option value="constant">Constant</option>
                                                    </>
                                                )}
                                            </select>
                                        </div>

                                        {/* Nominal Power */}
                                        <div>
                                            <label className="text-[10px] uppercase font-bold text-muted mb-1.5 block">
                                                Nominal Power (kW)
                                            </label>
                                            <input
                                                type="number"
                                                step="0.1"
                                                min="0"
                                                value={entity.nominal_power_kw}
                                                onChange={(e) =>
                                                    updateEntity(index, { nominal_power_kw: Number(e.target.value) })
                                                }
                                                disabled={disabled}
                                                className="w-full rounded-lg border border-line/50 bg-surface2 px-3 py-2 text-sm text-text focus:border-accent focus:outline-none disabled:opacity-50"
                                            />
                                        </div>

                                        {/* Water Heater Specific Fields */}
                                        {isWaterHeater && (
                                            <>
                                                <div>
                                                    <label className="text-[10px] uppercase font-bold text-muted mb-1.5 block">
                                                        Max Hours Between Heating
                                                    </label>
                                                    <input
                                                        type="number"
                                                        step="1"
                                                        min="1"
                                                        max="24"
                                                        value={(entity as WaterHeaterEntity).max_hours_between_heating}
                                                        onChange={(e) =>
                                                            updateEntity(index, {
                                                                max_hours_between_heating: Number(e.target.value),
                                                            } as Partial<WaterHeaterEntity>)
                                                        }
                                                        disabled={disabled}
                                                        className="w-full rounded-lg border border-line/50 bg-surface2 px-3 py-2 text-sm text-text focus:border-accent focus:outline-none disabled:opacity-50"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="text-[10px] uppercase font-bold text-muted mb-1.5 block">
                                                        Min Spacing (hours)
                                                    </label>
                                                    <input
                                                        type="number"
                                                        step="0.5"
                                                        min="0"
                                                        max="12"
                                                        value={(entity as WaterHeaterEntity).water_min_spacing_hours}
                                                        onChange={(e) =>
                                                            updateEntity(index, {
                                                                water_min_spacing_hours: Number(e.target.value),
                                                            } as Partial<WaterHeaterEntity>)
                                                        }
                                                        disabled={disabled}
                                                        className="w-full rounded-lg border border-line/50 bg-surface2 px-3 py-2 text-sm text-text focus:border-accent focus:outline-none disabled:opacity-50"
                                                    />
                                                </div>
                                            </>
                                        )}

                                        {/* EV Charger Specific Fields */}
                                        {!isWaterHeater && (
                                            <>
                                                <div>
                                                    <label className="text-[10px] uppercase font-bold text-muted mb-1.5 block">
                                                        Min SoC (%)
                                                    </label>
                                                    <input
                                                        type="number"
                                                        step="1"
                                                        min="0"
                                                        max="100"
                                                        value={(entity as EVChargerEntity).min_soc_percent}
                                                        onChange={(e) =>
                                                            updateEntity(index, {
                                                                min_soc_percent: Number(e.target.value),
                                                            } as Partial<EVChargerEntity>)
                                                        }
                                                        disabled={disabled}
                                                        className="w-full rounded-lg border border-line/50 bg-surface2 px-3 py-2 text-sm text-text focus:border-accent focus:outline-none disabled:opacity-50"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="text-[10px] uppercase font-bold text-muted mb-1.5 block">
                                                        Target SoC (%)
                                                    </label>
                                                    <input
                                                        type="number"
                                                        step="1"
                                                        min="0"
                                                        max="100"
                                                        value={(entity as EVChargerEntity).target_soc_percent}
                                                        onChange={(e) =>
                                                            updateEntity(index, {
                                                                target_soc_percent: Number(e.target.value),
                                                            } as Partial<EVChargerEntity>)
                                                        }
                                                        disabled={disabled}
                                                        className="w-full rounded-lg border border-line/50 bg-surface2 px-3 py-2 text-sm text-text focus:border-accent focus:outline-none disabled:opacity-50"
                                                    />
                                                </div>
                                            </>
                                        )}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                ))}
            </div>

            {enabledCount === 0 && entities.length > 0 && (
                <div className="p-3 bg-bad/10 border border-bad/30 rounded-xl text-xs text-bad flex items-start gap-2">
                    <span className="text-base leading-none mt-0.5">⚠️</span>
                    <div>
                        <strong>No {title.toLowerCase()} enabled.</strong>
                        <p className="mt-1 opacity-80">Enable at least one device for optimization to work.</p>
                    </div>
                </div>
            )}
        </div>
    )
}
