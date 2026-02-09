/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * PowerFlowCard.tsx
 *
 * Production-grade energy flow visualization with Particles + Hub Glow animation.
 * Registry-driven nodes for extensibility + auto-positioning.
 */

import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { NODE_REGISTRY, type PowerFlowData, type FlowNodeConfig } from './PowerFlowRegistry'
import type { LucideIcon } from 'lucide-react'

// =============================================================================
// TYPES
// =============================================================================

interface PowerFlowCardProps {
    data: PowerFlowData
    systemConfig?: any
    compact?: boolean
}

// =============================================================================
// PARTICLE STREAM (Clean, regular spacing, speed = f(power))
// =============================================================================

interface ParticleStreamProps {
    from: { x: number; y: number }
    to: { x: number; y: number }
    power: number
    color: string
    reverse?: boolean
}

function ParticleStream({ from, to, power, color, reverse }: ParticleStreamProps) {
    const absPower = Math.abs(power)
    const actualFrom = reverse ? to : from
    const actualTo = reverse ? from : to

    // Fixed particle count, speed proportional to power
    const particleCount = 4
    // Duration inversely proportional to power: more power = faster
    // At 0.5 kW → 3s, at 5 kW → 0.8s
    const duration = Math.max(3.5 - absPower * 0.6, 0.8)

    return (
        <g>
            {/* Always visible base line */}
            <line
                x1={actualFrom.x}
                y1={actualFrom.y}
                x2={actualTo.x}
                y2={actualTo.y}
                stroke={color}
                strokeWidth={2}
                strokeOpacity={1}
            />
            {/* Animated particles - clean, regular spacing */}
            {absPower > 0.05 &&
                Array.from({ length: particleCount }).map((_, i) => (
                    <motion.circle
                        key={i}
                        r={3.5}
                        fill={color}
                        initial={{ opacity: 0 }}
                        animate={{
                            cx: [actualFrom.x, actualTo.x],
                            cy: [actualFrom.y, actualTo.y],
                            opacity: [0, 0.85, 0.85, 0],
                        }}
                        transition={{
                            duration,
                            repeat: Infinity,
                            delay: (i / particleCount) * duration,
                            ease: 'linear',
                        }}
                    />
                ))}
        </g>
    )
}

// =============================================================================
// NODE WITH GLOW
// =============================================================================

interface NodeProps {
    x: number
    y: number
    node: FlowNodeConfig
    label: string
    value: string
    subValue?: string
    glowIntensity: number
    isCharging?: boolean
    compact?: boolean
    resolvedColor: string
    resolvedIcon: LucideIcon
}

function Node({
    x,
    y,
    node,
    value,
    subValue,
    glowIntensity,
    isCharging,
    compact,
    resolvedColor,
    resolvedIcon,
}: NodeProps) {
    const iconSize = compact ? 18 : 25

    // Pill shape dimensions
    const pillWidth = compact ? 90 : 110
    const pillHeight = compact ? 40 : 50
    const pillRadius = pillHeight / 2

    const IconComponent = (isCharging && node.lucideIconCharging) || resolvedIcon

    // TWEAK THESE VALUES:
    const bgOpacity = 1.0 // Background opacity (0.0 to 1.0)
    const textColor = '#1d1d1dff' // Text color (hex or rgb)

    return (
        <g transform={`translate(${x}, ${y})`}>
            {/* Glow effect */}
            {glowIntensity > 0.1 && (
                <motion.rect
                    x={-pillWidth / 2 - 10}
                    y={-pillHeight / 2 - 10}
                    width={pillWidth + 20}
                    height={pillHeight + 20}
                    rx={pillRadius + 10}
                    ry={pillRadius + 10}
                    fill={resolvedColor}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 0.1 + glowIntensity * 0.15 }}
                    transition={{ duration: 0.4 }}
                />
            )}
            {/* Pill background */}
            <rect
                x={-pillWidth / 2}
                y={-pillHeight / 2}
                width={pillWidth}
                height={pillHeight}
                rx={pillRadius}
                ry={pillRadius}
                fill={resolvedColor}
                fillOpacity={bgOpacity}
            />
            {/* Icon on the left (centered in the left radius) */}
            <foreignObject
                x={-pillWidth / 2 + pillRadius - iconSize / 2}
                y={-iconSize / 2}
                width={iconSize}
                height={iconSize}
            >
                <IconComponent size={iconSize} style={{ color: textColor }} strokeWidth={1.5} />
            </foreignObject>
            {/* Value (power) - top right */}
            <text
                x={-pillWidth / 2 + pillRadius + 20}
                y={-2}
                textAnchor="start"
                fill={textColor}
                fontSize={compact ? '11' : '12'}
                fontWeight="600"
            >
                {value}
            </text>
            {/* Subvalue (daily energy) - bottom right */}
            {subValue && (
                <text
                    x={-pillWidth / 2 + pillRadius + 20}
                    y={12}
                    textAnchor="start"
                    fill={textColor}
                    fontSize={compact ? '8' : '10'}
                    opacity={0.7}
                >
                    {subValue}
                </text>
            )}
        </g>
    )
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function PowerFlowCard({ data, systemConfig, compact = false }: PowerFlowCardProps) {
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
            // House and Grid are always visible (no configKey)
            if (node.configKey) {
                const toggleValue = configMap[node.configKey]
                if (toggleValue !== undefined) {
                    if (toggleValue === false) return false
                } else {
                    // Fallback: show standard hardware if toggle not found
                    if (!['solar', 'battery', 'water'].includes(node.id)) return false
                }
            }

            // 2. Dynamic Visibility Check (Rev UI18)
            if (node.shouldRender) {
                return node.shouldRender(data, configMap)
            }

            return true
        })
    }, [configMap, data])

    // 3. Dynamic positioning logic
    const { nodes } = useMemo(() => {
        const baseScale = compact ? 0.75 : 1
        const targetCenterX = compact ? 150 : 200
        const targetCenterY = compact ? 117 : 161
        const offX = (p: number) => (p - 200) * baseScale + targetCenterX
        const offY = (p: number) => (p - 142.5) * baseScale + targetCenterY

        const topNodes = enabledNodes.filter((n) => n.id === 'solar' || n.id === 'water')
        const bottomNodes = enabledNodes.filter((n) => n.id === 'battery' || n.id === 'grid' || n.id === 'ev')

        const pos: Record<string, { x: number; y: number }> = {}

        // Hub (House) is always at center
        pos['house'] = { x: offX(200), y: offY(142.5) }

        // Top Row Positioning
        topNodes.forEach((n) => {
            let x = 200
            if (topNodes.length === 2) {
                x = n.id === 'solar' ? 100 : 300
            }
            pos[n.id] = { x: offX(x), y: offY(50) }
        })

        // Bottom Row Positioning
        bottomNodes.forEach((n, i) => {
            let x = 200
            if (bottomNodes.length === 2) {
                // If 2 nodes, use the original 100/300 split
                if (n.id === 'grid') x = 100
                else if (n.id === 'battery') x = 300
                else x = i === 0 ? 100 : 300 // Fallback for other combinations
            } else if (bottomNodes.length === 3) {
                // Space 3 nodes evenly
                if (i === 0) x = 70
                else if (i === 1) x = 200
                else x = 330
            }
            pos[n.id] = { x: offX(x), y: offY(240) }
        })

        return { nodes: pos }
    }, [enabledNodes, compact])

    const viewBox = compact ? '0 0 300 260' : '0 0 400 330'

    return (
        <svg viewBox={viewBox} className="w-full h-full" preserveAspectRatio="xMidYMid meet">
            {/* Connections with particles (Always connect to house) */}
            {enabledNodes.map((node) => {
                if (node.id === 'house') return null
                if (!nodes[node.id]) return null

                // Determine flow power and direction
                // Solar -> House: + is towards house
                // Water -> House: (actually House -> Water)
                // Battery, Grid: + is towards house (import/discharge), - is away (export/charge)
                let power = 0
                let reverse = false
                const color = (typeof node.color === 'function' ? node.color(data) : node.color) as string

                switch (node.id) {
                    case 'solar':
                        power = data.solar.kw
                        break
                    case 'water':
                        power = data.water.kw
                        reverse = true // House -> Water
                        break
                    case 'ev':
                        power = data.ev?.kw ?? 0
                        reverse = true // House -> EV
                        break
                    case 'battery':
                        power = Math.abs(data.battery.kw)
                        reverse = data.battery.kw < 0 // House -> Battery if negative
                        break
                    case 'grid':
                        power = Math.abs(data.grid.kw)
                        reverse = data.grid.kw < 0 // House -> Grid if negative
                        break
                }

                return (
                    <ParticleStream
                        key={`flow-${node.id}`}
                        from={nodes[node.id]}
                        to={nodes.house}
                        power={power}
                        color={color}
                        reverse={reverse}
                    />
                )
            })}

            {/* Nodes with glow */}
            {enabledNodes.map((node) => {
                if (!nodes[node.id]) return null

                const resolvedLabel = typeof node.label === 'function' ? node.label(data) : node.label

                const resolvedColor = (typeof node.color === 'function' ? node.color(data) : node.color) as string
                const resolvedIcon = (
                    typeof node.lucideIcon === 'function' ? node.lucideIcon(data) : node.lucideIcon
                ) as LucideIcon

                return (
                    <Node
                        key={node.id}
                        x={nodes[node.id].x}
                        y={nodes[node.id].y}
                        node={node}
                        label={resolvedLabel}
                        value={node.valueAccessor(data)}
                        subValue={node.subValueAccessor?.(data)}
                        glowIntensity={node.glowIntensityAccessor(data)}
                        isCharging={node.isChargingAccessor?.(data)}
                        compact={compact}
                        resolvedColor={resolvedColor}
                        resolvedIcon={resolvedIcon}
                    />
                )
            })}
        </svg>
    )
}
