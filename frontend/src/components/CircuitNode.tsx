import { LucideIcon } from 'lucide-react'

interface CircuitNodeProps {
    x: number
    y: number
    label: string
    subValue?: string
    value?: string
    color: string
    icon?: LucideIcon
    isActive?: boolean
    variant?: 'bracket' | 'circle'
    onInteract?: () => void
}

export function CircuitNode({
    x,
    y,
    label,
    subValue,
    value,
    color,
    icon: Icon,
    isActive = false,
    variant = 'bracket',
    onInteract,
}: CircuitNodeProps) {
    // Circle variant (House)
    if (variant === 'circle') {
        const r = 30 // Reduced diameter as requested
        const interactionProps = onInteract
            ? {
                  onClick: onInteract,
                  style: { cursor: 'pointer' },
              }
            : {}

        return (
            <g transform={`translate(${x}, ${y})`} {...interactionProps}>
                {isActive && (
                    <circle r={r + 4} fill={color} fillOpacity="0.15" filter={`drop-shadow(0 0 8px ${color})`} />
                )}
                <circle
                    r={r}
                    fill="rgb(var(--color-surface))"
                    stroke={isActive ? color : 'rgb(var(--color-line))'}
                    strokeWidth={isActive ? 2 : 1}
                />
                {Icon && (
                    <foreignObject
                        x={-16}
                        y={-16}
                        width={32}
                        height={32}
                        style={{ color: isActive ? color : 'rgb(var(--color-muted))' }}
                    >
                        <Icon size={32} strokeWidth={1.5} />
                    </foreignObject>
                )}
                {/* Value Text Below Node */}
                <text
                    x={0}
                    y={r + 16}
                    textAnchor="middle"
                    fill={isActive ? color : 'rgb(var(--color-text))'}
                    fontSize="12"
                    fontFamily="JetBrains Mono, monospace"
                    fontWeight="bold"
                >
                    {value}
                </text>
            </g>
        )
    }

    // Bracket variant (Peripheral Nodes)
    // SVG Brackets to cover the whole node (Label + Value + SubValue)
    const bW = 46 // Bracket Width (half) ALSO CHANGE IN POWERFLOWCARD.TSX L116-117
    const bH = 22 // Bracket Height (half)

    // Brackets: Vertical line with rounded corners
    // Path: M (start) A (corner) L (vertical) A (corner) L (end)
    const r = 4 // Corner radius (adjustable)
    const bracketSize = 12 // Horizontal span

    // Left Bracket: [-bW+s, -bH] -> [-bW+r, -bH] arc -> [-bW, -bH+r] -> [-bW, bH-r] arc -> [-bW+r, bH] -> [-bW+s, bH]
    const bracketPathLeft = `
        M ${-bW + bracketSize} ${-bH}
        L ${-bW + r} ${-bH}
        Q ${-bW} ${-bH} ${-bW} ${-bH + r}
        L ${-bW} ${bH - r}
        Q ${-bW} ${bH} ${-bW + r} ${bH}
        L ${-bW + bracketSize} ${bH}
    `

    // Right Bracket: [bW-s, -bH] -> [bW-r, -bH] arc -> [bW, -bH+r] -> [bW, bH-r] arc -> [bW+r, bH] -> [bW-s, bH]
    const bracketPathRight = `
        M ${bW - bracketSize} ${-bH}
        L ${bW - r} ${-bH}
        Q ${bW} ${-bH} ${bW} ${-bH + r}
        L ${bW} ${bH - r}
        Q ${bW} ${bH} ${bW - r} ${bH}
        L ${bW - bracketSize} ${bH}
    `

    // Interaction props
    const interactionProps = onInteract
        ? {
              onClick: onInteract,
              style: { cursor: 'pointer' },
          }
        : {}

    return (
        <g transform={`translate(${x}, ${y})`} {...interactionProps}>
            {/* Left Bracket */}
            <path
                d={bracketPathLeft}
                fill="none"
                stroke={isActive ? color : 'rgb(var(--color-muted))'}
                strokeWidth="1.5"
            />

            {/* Right Bracket */}
            <path
                d={bracketPathRight}
                fill="none"
                stroke={isActive ? color : 'rgb(var(--color-muted))'}
                strokeWidth="1.5"
            />

            {/* Content Stack */}

            {/* 1. Label (Top) */}
            <text
                x={0}
                y={-18}
                textAnchor="middle"
                fill="rgb(var(--color-muted))"
                fontSize="10"
                fontFamily="JetBrains Mono, monospace"
                className="uppercase tracking-wider"
            >
                {label}
            </text>

            {/* 2. Main Value (Middle) */}
            <text
                x={0}
                y={4}
                textAnchor="middle"
                fill={isActive ? color : 'rgb(var(--color-text))'}
                fontSize="14"
                fontFamily="JetBrains Mono, monospace"
                fontWeight="bold"
            >
                {value || '0 kW'}
            </text>

            {/* 3. SubValue (Bottom) */}
            {subValue && (
                <text
                    x={0}
                    y={22}
                    textAnchor="middle"
                    fill={isActive ? 'rgb(var(--color-text))' : 'rgb(var(--color-muted))'}
                    fontSize="11"
                    fontFamily="JetBrains Mono, monospace"
                >
                    {subValue}
                </text>
            )}

            {/* Connection Ports - Aligned with Bracket Centers vertically?
                Or keep at top/bottom of the group?
                Let's place them at top/bottom center for vertical connections,
                or left/right center for horizontal connections.
                Current Layout (Horizontal) connects Left/Right.

                If wires connect to the "Back" of the brackets, that's:
                Left Node: Connects Right side.
                Right Node: Connects Left side.
            */}
        </g>
    )
}
