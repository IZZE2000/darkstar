import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { HelpCircle } from 'lucide-react'

interface TooltipProps {
    text?: string
    className?: string
}

export default function Tooltip({ text, className = '' }: TooltipProps) {
    const [isVisible, setIsVisible] = useState(false)
    const [coords, setCoords] = useState({ top: 0, left: 0 })
    const triggerRef = useRef<HTMLButtonElement>(null)

    const updatePosition = () => {
        if (triggerRef.current) {
            const rect = triggerRef.current.getBoundingClientRect()
            setCoords({
                top: rect.top, // We will offset upwards using CSS transform
                left: rect.left,
            })
        }
    }

    // Update position on scroll/resize if visible
    useEffect(() => {
        if (isVisible) {
            updatePosition()
            window.addEventListener('scroll', updatePosition, true)
            window.addEventListener('resize', updatePosition)
        }
        return () => {
            window.removeEventListener('scroll', updatePosition, true)
            window.removeEventListener('resize', updatePosition)
        }
    }, [isVisible])

    if (!text) return null

    return (
        <div className={`inline-block ${className}`}>
            <button
                ref={triggerRef}
                type="button"
                className="ml-1.5 text-muted/60 hover:text-accent transition-colors cursor-help"
                onMouseEnter={() => {
                    updatePosition()
                    setIsVisible(true)
                }}
                onMouseLeave={() => setIsVisible(false)}
                onFocus={() => {
                    updatePosition()
                    setIsVisible(true)
                }}
                onBlur={() => setIsVisible(false)}
            >
                <HelpCircle className="w-3.5 h-3.5" />
            </button>

            {isVisible &&
                createPortal(
                    <div
                        className="fixed z-[9999] w-64 p-2.5 text-xs bg-surface2 border border-line rounded-lg shadow-xl"
                        style={{
                            top: coords.top - 8, // 8px gap above icon
                            left: coords.left - 10, // Slight optical adjustment
                            transform: 'translateY(-100%)', // Shift up by its own height
                        }}
                    >
                        <div className="text-muted leading-relaxed">{text}</div>
                        {/* Arrow (Pointing down) */}
                        <div className="absolute w-2 h-2 bg-surface2 border-r border-b border-line transform rotate-45 left-4 -bottom-1" />
                    </div>,
                    document.body,
                )}
        </div>
    )
}
