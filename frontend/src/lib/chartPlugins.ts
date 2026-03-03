import type { Plugin } from 'chart.js'

interface NowLineData {
    nowPct?: number | null
    labels?: string[]
}

export const nowLinePlugin: Plugin = {
    id: 'nowLine',
    afterDatasetsDraw(chart) {
        const { ctx, chartArea: { top, bottom }, scales: { x } } = chart
        const nowPct = (chart.config.options as any)?.nowPct

        if (typeof nowPct !== 'number' || nowPct < 0 || nowPct > 1) return

        const totalLabels = data.labels?.length || 0
        if (totalLabels < 2) return

        // Calculate fractional position
        const fractionalIndex = nowPct * (totalLabels - 1)
        const idx1 = Math.floor(fractionalIndex)
        const idx2 = Math.ceil(fractionalIndex)
        const ratio = fractionalIndex - idx1

        const x1 = x.getPixelForValue(idx1)
        const x2 = x.getPixelForValue(idx2)
        const xPos = x1 + (x2 - x1) * ratio

        // Skip if outside visible area (respects zoom)
        if (xPos < x.left || xPos > x.right) return

        // Draw line
        ctx.save()
        ctx.beginPath()
        ctx.strokeStyle = '#e879f9'  // Pink/magenta for consistency
        ctx.lineWidth = 1.5
        ctx.shadowColor = '#e879f9'
        ctx.shadowBlur = 10
        ctx.setLineDash([4, 4])
        ctx.moveTo(xPos, top)
        ctx.lineTo(xPos, bottom)
        ctx.stroke()
        ctx.setLineDash([])

        // Draw label
        ctx.fillStyle = '#e879f9'
        ctx.textAlign = 'center'
        ctx.font = 'bold 10px monospace'
        ctx.fillText('NOW', xPos, top - 8)
        ctx.restore()
    },
}
