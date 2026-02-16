/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * PowerFlowCard.tsx
 *
 * Schematic / Circuit Board style energy flow visualization.
 * Uses CircuitNode (Chips) and CircuitPath (Traces) for a sci-fi aesthetic.
 */

import { useMemo, useState, useCallback, useEffect } from 'react'
import { NODE_REGISTRY, type PowerFlowData } from './PowerFlowRegistry'
import type { LucideIcon } from 'lucide-react'
import { CircuitNode } from './CircuitNode'
import { CircuitPath } from './CircuitPath'
import { Plug } from 'lucide-react'

// =============================================================================
// TYPES
// =============================================================================

interface PowerFlowCardProps {
    data: PowerFlowData
    systemConfig?: any
    compact?: boolean
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function PowerFlowCard({ data, systemConfig, compact = false }: PowerFlowCardProps) {
    // Rev F64: EV Tooltip state
    const [showEvTooltip, setShowEvTooltip] = useState(false)

    // Close tooltip on outside click (mobile)
    const handleOutsideClick = useCallback(() => {
        setShowEvTooltip(false)
    }, [])

    useEffect(() => {
        if (showEvTooltip) {
            // Rev F64: Defer listener registration to next tick to avoid
            // the same click that opened the tooltip from immediately closing it
            const timeoutId = setTimeout(() => {
                document.addEventListener('click', handleOutsideClick)
                document.addEventListener('touchstart', handleOutsideClick)
            }, 0)
            return () => {
                clearTimeout(timeoutId)
                document.removeEventListener('click', handleOutsideClick)
                document.removeEventListener('touchstart', handleOutsideClick)
            }
        }
    }, [showEvTooltip, handleOutsideClick])

    const handleEvInteract = useCallback((e: React.MouseEvent | React.TouchEvent) => {
        e.stopPropagation()
        setShowEvTooltip((prev) => !prev)
    }, [])

    // Build EV tooltip content - dynamic sizing and centered
    const evTooltipContent = useMemo(() => {
        if (!data.evChargers || data.evChargers.length === 0 || compact) return null

        const evCount = data.evChargers.length
        const header = evCount > 1 ? `${evCount} EVs Connected` : data.evChargers[0]?.name || 'EV'

        return (
            <div
                className="bg-surface-elevated"
                style={{
                    borderRadius: '8px',
                    border: '1px solid rgba(255,255,255,0.2)',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.7)',
                    padding: '10px 14px',
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '11px',
                    color: '#e2e8f0',
                    maxHeight: '180px',
                    overflowY: 'auto',
                    minWidth: '180px',
                    width: 'max-content',
                    zIndex: 1000,
                    opacity: 0.98,
                }}
            >
                <div
                    style={{
                        fontWeight: 'bold',
                        marginBottom: '6px',
                        color: 'rgb(var(--color-ai))',
                        whiteSpace: 'nowrap',
                    }}
                >
                    {header}
                </div>
                {data.evChargers.map((ev, idx) => (
                    <div
                        key={idx}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '4px 0',
                            borderTop: idx > 0 ? '1px solid rgba(255,255,255,0.1)' : 'none',
                            whiteSpace: 'nowrap',
                        }}
                    >
                        <Plug
                            size={12}
                            style={{
                                color: ev.pluggedIn ? 'rgb(var(--color-good))' : '#64748b',
                                flexShrink: 0,
                            }}
                        />
                        <span style={{ flex: 1 }}>{ev.name}</span>
                        <span>{ev.kw.toFixed(1)} kW</span>
                        {ev.soc !== null && <span>{ev.soc.toFixed(0)}%</span>}
                    </div>
                ))}
            </div>
        )
    }, [data.evChargers, compact])

    // 1. Flatten config into dot-notation map for easy lookup
    const configMap = useMemo(() => {
        if (!systemConfig || typeof systemConfig !== 'object') return null
        const map: Record<string, any> = {}
        const flatten = (obj: any, prefix = '') => {
            if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
                for (const k in obj) {
                    const path = prefix ? `${prefix}.${k}` : k
                    if (typeof obj[k] === 'object' && !Array.isArray(obj[k])) {
                        flatten(obj[k], path)
                    } else {
                        map[path] = obj[k]
                    }
                }
            }
        }
        flatten(systemConfig)
        return map
    }, [systemConfig])

    // 2. Filter enabled nodes based on config toggles
    const enabledNodes = useMemo(() => {
        // If config is null/loading, show standard hardware to prevent blank UI
        if (!configMap) {
            return NODE_REGISTRY.filter((n) => !n.configKey || ['solar', 'battery', 'water'].includes(n.id))
        }

        return NODE_REGISTRY.filter((node) => {
            // 1. Config Toggle Check
            if (node.configKey) {
                const toggleValue = configMap[node.configKey]
                if (toggleValue !== undefined) {
                    if (toggleValue === false) return false
                } else {
                    // Fallback: show standard hardware if toggle not found
                    if (!['solar', 'battery', 'water'].includes(node.id)) return false
                }
            }

            // 2. Dynamic Visibility Check
            if (node.shouldRender) {
                return node.shouldRender(data, configMap)
            }

            return true
        })
    }, [configMap, data])

    // 3. Layout Configuration (Schematic Grid - Horizontal)
    // House is central hub. Inputs Left, Outputs Right.
    const layout = useMemo(() => {
        // Compact: 300x260. Standard: 400x330.
        const cx = compact ? 150 : 200 // Center X
        const cy = compact ? 130 : 165 // Center Y
        const dx = compact ? 100 : 120 // Horizontal Spacing
        const dy = compact ? 70 : 80 // Vertical Spacing

        const pos: Record<string, { x: number; y: number }> = {
            house: { x: cx, y: cy },
            // Sources (Left Column)
            solar: { x: cx - dx, y: cy - dy },
            grid: { x: cx - dx, y: cy + dy },
            // Storage/Loads (Right Column)
            battery: { x: cx + dx, y: cy - dy },
            water: { x: cx + dx, y: cy },
            ev: { x: cx + dx, y: cy + dy },
        }

        return { pos, scale: compact ? 0.8 : 1.0 }
    }, [compact])

    // 4. Port Configuration helper
    const getPorts = (fromId: string, toId: string) => {
        // Horizontal Schematic Flow:
        // Left Nodes (Solar, Grid) -> House (Center)
        // House (Center) -> Right Nodes (Battery, EV, Water)

        const fromPos = layout.pos[fromId]
        const toPos = layout.pos[toId]

        if (!fromPos || !toPos) return { start: { x: 0, y: 0 }, end: { x: 0, y: 0 } }

        // Node Dimensions (Approx for port calc)
        // House Circle: r=32 (CircuitNode.tsx)
        // Bracket Nodes: bW=42 (CircuitNode.tsx). We use 42 + 2 padding = 44.

        // EDIT HERE: Sync these with CircuitNode.tsx if you change sizes there!
        const HOUSE_R = 32 // 32 + 4 padding
        const BRACKET_W_HALF = 46 // bW (42) + 2 padding

        // Defaults
        let start = { x: fromPos.x, y: fromPos.y }
        let end = { x: toPos.x, y: toPos.y }

        // Logic: Connect "Inner" sides to "Outer" sides

        // Solar -> House (Left -> Center)
        if (fromId === 'solar' && toId === 'house') {
            start = { x: fromPos.x + BRACKET_W_HALF, y: fromPos.y }
            end = { x: toPos.x - HOUSE_R, y: toPos.y - 15 }
        }

        // Grid -> House (Left -> Center)
        if (fromId === 'grid' && toId === 'house') {
            start = { x: fromPos.x + BRACKET_W_HALF, y: fromPos.y }
            end = { x: toPos.x - HOUSE_R, y: toPos.y + 15 }
        }

        // House -> Battery (Center -> Right)
        if (fromId === 'house' && toId === 'battery') {
            start = { x: fromPos.x + HOUSE_R, y: fromPos.y - 15 }
            end = { x: toPos.x - BRACKET_W_HALF, y: toPos.y }
        }

        // House -> Water (Center -> Right)
        if (fromId === 'house' && toId === 'water') {
            start = { x: fromPos.x + HOUSE_R, y: fromPos.y }
            end = { x: toPos.x - BRACKET_W_HALF, y: toPos.y }
        }

        // House -> EV (Center -> Right)
        if (fromId === 'house' && toId === 'ev') {
            start = { x: fromPos.x + HOUSE_R, y: fromPos.y + 15 }
            end = { x: toPos.x - BRACKET_W_HALF, y: toPos.y }
        }

        return { start, end }
    }

    const viewBox = compact ? '0 0 300 260' : '0 0 400 330'

    return (
        <svg viewBox={viewBox} className="w-full h-full" preserveAspectRatio="xMidYMid meet">
            <defs>
                {/* Grid Pattern - centered and adaptive */}
                <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse" x="-10" y="-10">
                    <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgb(var(--color-line))" strokeWidth="0.5" />
                </pattern>
            </defs>
            {/* Grid background - visible in both modes */}
            <rect width="100%" height="100%" fill="url(#grid)" opacity="0.7" />

            {/* 1. PATHS (Traces) - Render first so they are behind nodes */}
            {enabledNodes.map((node) => {
                const nodePos = layout.pos[node.id]
                if (!nodePos) return null
                // Skip House path/pill relative to itself
                if (node.id === 'house') return null

                // Determine flow metrics
                let power = 0
                let isActive = false
                let flowFrom: string = node.id

                // Direction logic:
                // We always DRAW the path Left -> Right.

                let drawFrom = node.id
                let drawTo = 'house'

                // Loads are Right of House -> Draw House -> Load
                if (['battery', 'ev', 'water'].includes(node.id)) {
                    drawFrom = 'house' as any
                    drawTo = node.id
                }

                // Value logic
                switch (node.id) {
                    case 'solar':
                        power = data.solar.kw
                        isActive = power > 0
                        break
                    case 'water':
                        power = data.water.kw
                        isActive = power > 0
                        flowFrom = 'house' as any // Consumption
                        break
                    case 'ev':
                        power = data.ev?.kw ?? 0
                        isActive = power > 0
                        flowFrom = 'house' as any
                        break
                    case 'battery':
                        power = Math.abs(data.battery.kw)
                        isActive = power > 0
                        if (data.battery.kw < 0) {
                            // Charging (House -> Battery)
                            flowFrom = 'house' as any
                        } else {
                            // Discharging (Battery -> House)
                            flowFrom = 'battery'
                        }
                        break
                    case 'grid':
                        power = Math.abs(data.grid.kw)
                        isActive = power > 0
                        if (data.grid.kw < 0) {
                            // Export (House -> Grid)
                            flowFrom = 'house' as any
                        } else {
                            // Import (Grid -> House)
                            flowFrom = 'grid'
                        }
                        break
                }

                // Determine endpoints based on standard "Wire" layout
                let { start, end } = getPorts(drawFrom, drawTo)

                // If flow is reversed relative to Draw Direction, swap start/end
                // Draw Direction: Left -> Right (mostly)
                // Flow Direction check:

                if ((flowFrom as string) === 'house' && (drawFrom as string) !== 'house') {
                    // e.g. Grid Export (House->Grid). drawFrom='grid'. flowFrom='house'.
                    const ports = getPorts(drawFrom, drawTo)
                    start = ports.end
                    end = ports.start
                } else if ((flowFrom as string) !== 'house' && (drawFrom as string) === 'house') {
                    // e.g. Battery Discharge (Batt->House). drawFrom='house'. flowFrom='battery'.
                    const ports = getPorts(drawFrom, drawTo)
                    start = ports.end
                    end = ports.start
                }

                const color = (typeof node.color === 'function' ? node.color(data) : node.color) as string
                // Removed formattedValue pill - value is now in Node

                return (
                    <CircuitPath
                        key={`trace-${node.id}`}
                        from={start}
                        to={end}
                        color={color}
                        isActive={isActive}
                        flowRate={Math.max(power * 0.5, 0.5)}
                    />
                )
            })}

            {/* 2. NODES (Chips) */}
            {enabledNodes.map((node) => {
                const pos = layout.pos[node.id]
                if (!pos) return null

                const resolvedLabel = typeof node.label === 'function' ? node.label(data) : node.label
                const resolvedColor = (typeof node.color === 'function' ? node.color(data) : node.color) as string
                const resolvedIcon = (
                    typeof node.lucideIcon === 'function' ? node.lucideIcon(data) : node.lucideIcon
                ) as LucideIcon

                let isActive = false
                switch (node.id) {
                    case 'solar':
                        isActive = data.solar.kw > 0
                        break
                    case 'grid':
                        isActive = Math.abs(data.grid.kw) > 0
                        break
                    case 'battery':
                        isActive = Math.abs(data.battery.kw) > 0
                        break
                    case 'ev':
                        isActive = (data.ev?.kw ?? 0) > 0 || (data.evPluggedIn ?? false)
                        break
                    case 'water':
                        isActive = data.water.kw > 0
                        break
                    case 'house':
                        isActive = true
                        break
                }

                const valueStr = node.valueAccessor(data)

                return (
                    <CircuitNode
                        key={node.id}
                        x={pos.x}
                        y={pos.y}
                        label={resolvedLabel}
                        value={valueStr}
                        subValue={node.subValueAccessor?.(data)}
                        color={resolvedColor}
                        icon={resolvedIcon}
                        isActive={isActive}
                        variant={node.id === 'house' ? 'circle' : 'bracket'}
                        // Rev F64: EV Tooltip - tap/click handler for EV node with multiple EVs
                        onInteract={node.id === 'ev' && evTooltipContent ? handleEvInteract : undefined}
                    />
                )
            })}

            {/* Rev F64: Render tooltip as foreignObject if shown - centered in card */}
            {showEvTooltip && evTooltipContent && (
                <foreignObject
                    x={compact ? 70 : 100}
                    y={compact ? 40 : 50}
                    width={compact ? 160 : 200}
                    height={compact ? 120 : 160}
                    style={{ overflow: 'visible' }}
                >
                    <div style={{ display: 'flex', justifyContent: 'center' }}>{evTooltipContent}</div>
                </foreignObject>
            )}
        </svg>
    )
}
