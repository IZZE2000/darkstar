import { motion } from 'framer-motion'
import { useMemo } from 'react'

interface Point {
    x: number
    y: number
}

interface CircuitPathProps {
    from: Point
    to: Point
    color?: string
    isActive?: boolean
    flowRate?: number
}

export function CircuitPath({
    from,
    to,
    color = '#06b6d4', // Cyan default
    isActive = false,
    flowRate = 1,
}: CircuitPathProps) {
    // Calculate Bezier Control Points once for reuse
    const dx = to.x - from.x
    const cp1 = { x: from.x + dx * 0.5, y: from.y }
    const cp2 = { x: to.x - dx * 0.5, y: to.y }

    // 1. Calculate Bezier Path 'd' attribute for "Circuit-like" routing
    // Force Horizontal Bias for this layout (Sources Left -> House -> Loads Right)
    const pathD = useMemo(() => {
        return `M ${from.x} ${from.y} C ${cp1.x} ${cp1.y} ${cp2.x} ${cp2.y} ${to.x} ${to.y}`
    }, [from, to, cp1.x, cp1.y, cp2.x, cp2.y])

    return (
        <g>
            {/* 1. Background Trace (Dim) */}
            <path
                d={pathD}
                fill="none"
                stroke="#1e293b" // Slate-800
                strokeWidth="2"
            />

            {/* 2. Active Flow Animation */}
            {isActive && (
                <motion.path
                    d={pathD}
                    fill="none"
                    stroke={color}
                    strokeWidth="2"
                    strokeDasharray="6 6"
                    initial={{ strokeDashoffset: 12 }}
                    animate={{ strokeDashoffset: 0 }}
                    transition={{
                        repeat: Infinity,
                        duration: 1 / Math.max(flowRate, 0.1),
                        ease: 'linear',
                    }}
                    style={{
                        filter: `drop-shadow(0 0 2px ${color})`,
                    }}
                />
            )}
        </g>
    )
}
