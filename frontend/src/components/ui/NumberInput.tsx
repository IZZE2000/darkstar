import React, { useRef } from 'react'

interface NumberInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
    value: string | number
    onChange: (value: string) => void
    step?: number
    min?: number
    max?: number
    className?: string
}

export const NumberInput: React.FC<NumberInputProps> = ({
    value,
    onChange,
    step = 1,
    min,
    max,
    className = '',
    disabled,
    ...props
}) => {
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    const updateValue = (increment: boolean) => {
        const currentVal = value === '' ? 0 : parseFloat(String(value))
        if (Number.isNaN(currentVal)) return

        // Calculate new value with precision handling for floats
        const precision = step.toString().split('.')[1]?.length || 0
        const delta = increment ? step : -step
        let newValue = parseFloat((currentVal + delta).toFixed(precision))

        // Clamp value
        if (min !== undefined && newValue < min) newValue = min
        if (max !== undefined && newValue > max) newValue = max

        onChange(String(newValue))
    }

    const startRepeating = (increment: boolean) => {
        if (disabled) return
        updateValue(increment)

        // Initial delay before rapid scrolling
        timeoutRef.current = setTimeout(() => {
            intervalRef.current = setInterval(() => {
                updateValue(increment)
            }, 50) // Speed of scrolling
        }, 500) // Delay before scrolling starts
    }

    const stopRepeating = () => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current)
        if (intervalRef.current) clearInterval(intervalRef.current)
    }

    // Handle styling classes
    const containerClasses = `relative flex items-center ${className}`
    const inputClasses = `w-full rounded-lg border border-line/50 bg-surface2 pl-3 pr-16 py-2 text-sm text-text focus:border-accent focus:outline-none appearance-none no-spinner text-left font-mono font-medium ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
    }`

    // Button base styles
    const btnClasses = `flex items-center justify-center w-7 h-7 rounded hover:bg-surface-elevated active:bg-accent/20 transition-colors text-muted hover:text-text disabled:opacity-30 disabled:cursor-not-allowed select-none`

    return (
        <div className={containerClasses}>
            <input
                ref={inputRef}
                type="number"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                step={step}
                min={min}
                max={max}
                disabled={disabled}
                className={inputClasses}
                {...props}
            />

            <div className="absolute right-1 top-0 bottom-0 flex items-center gap-0.5">
                <button
                    type="button"
                    className={btnClasses}
                    onMouseDown={() => startRepeating(false)}
                    onMouseUp={stopRepeating}
                    onMouseLeave={stopRepeating}
                    onTouchStart={() => startRepeating(false)}
                    onTouchEnd={stopRepeating}
                    disabled={disabled || (min !== undefined && Number(value) <= min)}
                    tabIndex={-1}
                    title="Decrease"
                >
                    −
                </button>
                <button
                    type="button"
                    className={btnClasses}
                    onMouseDown={() => startRepeating(true)}
                    onMouseUp={stopRepeating}
                    onMouseLeave={stopRepeating}
                    onTouchStart={() => startRepeating(true)}
                    onTouchEnd={stopRepeating}
                    disabled={disabled || (max !== undefined && Number(value) >= max)}
                    tabIndex={-1}
                    title="Increase"
                >
                    +
                </button>
            </div>
        </div>
    )
}
