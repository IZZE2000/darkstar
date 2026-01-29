import React, { useState, useEffect } from 'react'
import { Play, Pause, Loader2, Rocket } from 'lucide-react'
import { Api } from '../lib/api'
import { getSocket } from '../lib/socket'

interface QuickActionsProps {
    executorPaused: boolean
    onRefresh: () => void
}

interface PlannerProgress {
    phase: string
    elapsed_ms: number
}

export default function QuickActions({ executorPaused, onRefresh }: QuickActionsProps) {
    const [loading, setLoading] = useState<string | null>(null)
    const [plannerProgress, setPlannerProgress] = useState<PlannerProgress | null>(null)
    const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

    // Use prop directly
    const isPaused = executorPaused

    // WebSocket connection for planner progress
    useEffect(() => {
        const socket = getSocket()

        const handleProgress = (data: PlannerProgress) => {
            setPlannerProgress(data)
        }

        const handleScheduleUpdated = () => {
            setPlannerProgress({ phase: 'complete', elapsed_ms: 0 })
            setTimeout(() => setPlannerProgress(null), 2000)
            if (onRefresh) setTimeout(onRefresh, 500)
        }

        const handlePlannerError = () => {
            setPlannerProgress(null)
            setFeedback({ type: 'error', message: 'Planner failed' })
            setTimeout(() => setFeedback(null), 3000)
        }

        socket.on('planner_progress', handleProgress)
        socket.on('schedule_updated', handleScheduleUpdated)
        socket.on('planner_error', handlePlannerError)

        return () => {
            socket.off('planner_progress', handleProgress)
            socket.off('schedule_updated', handleScheduleUpdated)
            socket.off('planner_error', handlePlannerError)
        }
    }, [onRefresh])

    // Force re-render every second during solver phase to update progress bar
    useEffect(() => {
        if (plannerProgress?.phase === 'running_solver') {
            const interval = setInterval(() => {
                // Trigger re-render by updating elapsed_ms
                setPlannerProgress((prev) => (prev ? { ...prev, elapsed_ms: prev.elapsed_ms + 1000 } : null))
            }, 1000)
            return () => clearInterval(interval)
        }
    }, [plannerProgress?.phase])

    const handleRunPlanner = async () => {
        setPlannerProgress({ phase: 'starting', elapsed_ms: 0 })
        setFeedback(null)
        try {
            // Planner run
            await Api.runPlanner()

            // Executor run
            await Api.executor.run()
        } catch (err) {
            setFeedback({ type: 'error', message: err instanceof Error ? err.message : 'Failed' })
            setPlannerProgress(null)
        }
    }

    const handleTogglePause = async () => {
        setFeedback(null)
        setLoading('pause')
        try {
            if (isPaused) {
                await Api.executor.resume()
                setFeedback({ type: 'success', message: 'Executor resumed' })
                onRefresh?.()
            } else {
                await Api.executor.pause()
                setFeedback({ type: 'success', message: 'Executor paused - idle mode' })
                onRefresh?.()
            }
            setTimeout(() => setFeedback(null), 3000)
        } catch (err) {
            setFeedback({ type: 'error', message: err instanceof Error ? err.message : 'Failed' })
        } finally {
            setLoading(null)
        }
    }

    const getPlannerButtonText = () => {
        if (!plannerProgress) return 'Run Planner'

        const seconds = Math.floor(plannerProgress.elapsed_ms / 1000)
        const timeStr = seconds > 0 ? ` (${seconds}s)` : ''

        switch (plannerProgress.phase) {
            case 'starting':
                return 'Starting...'
            case 'fetching_inputs':
                return `Fetching inputs...${timeStr}`
            case 'fetching_prices':
                return `Fetching prices...${timeStr}`
            case 'applying_learning':
                return `Preparing...${timeStr}`
            case 'running_solver':
                return `Solving...${timeStr}`
            case 'applying_schedule':
                return `Applying...${timeStr}`
            case 'complete':
                return 'Done ✓'
            default:
                return `Planning...${timeStr}`
        }
    }

    const getProgressBarWidth = () => {
        if (!plannerProgress) return '0%'
        if (plannerProgress.phase === 'complete') return '100%'

        // Estimate progress based on phase and elapsed time
        const elapsed = plannerProgress.elapsed_ms / 1000 // seconds

        switch (plannerProgress.phase) {
            case 'starting':
            case 'fetching_inputs':
                return '5%'
            case 'fetching_prices':
                return '15%'
            case 'applying_learning':
                return '25%'
            case 'running_solver': {
                // Solver typically takes 3-10s, grow from 30% to 85%
                const solverProgress = Math.min(55, elapsed * 5.5)
                return `${30 + solverProgress}%`
            }
            case 'applying_schedule':
                return '90%'
            default:
                return '10%'
        }
    }

    const isPlanning = plannerProgress !== null

    return (
        <div className="relative">
            {/* Buttons grid */}
            <div className="grid grid-cols-2 gap-3">
                {/* 1. Run Planner */}
                <button
                    className={`relative overflow-hidden flex items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-[11px] font-semibold transition btn-glow-primary
                        ${
                            isPlanning
                                ? 'bg-surface border border-accent/50 text-accent cursor-wait'
                                : 'bg-accent hover:bg-accent2 text-[#100f0e]'
                        }`}
                    onClick={handleRunPlanner}
                    disabled={isPlanning}
                    title="Run planner and execute"
                >
                    {/* Progress Bar Background */}
                    <div
                        className={`absolute left-0 top-0 bottom-0 transition-all duration-500 ease-linear pointer-events-none ${
                            !isPlanning ? 'bg-transparent' : 'bg-accent/50'
                        }`}
                        style={{
                            width: getProgressBarWidth(),
                        }}
                    />

                    <div className="relative z-10 flex items-center gap-2">
                        {isPlanning && plannerProgress?.phase !== 'complete' ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <Rocket className="h-4 w-4" />
                        )}
                        <span>{getPlannerButtonText()}</span>
                    </div>
                </button>

                {/* 2. Executor Toggle (Pause/Resume) */}
                <button
                    className={`flex items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-[11px] font-semibold transition
                        ${
                            isPaused
                                ? 'bg-bad/80 text-white ring-2 ring-bad shadow-[0_0_20px_rgba(241,81,50,0.5)] animate-pulse'
                                : 'bg-good hover:bg-good/80 text-white btn-glow-green'
                        } ${loading === 'pause' ? 'opacity-60 cursor-wait' : ''}`}
                    onClick={handleTogglePause}
                    disabled={loading === 'pause'}
                    title={isPaused ? 'Resume executor' : 'Pause executor (idle mode)'}
                >
                    {isPaused ? (
                        <>
                            <Play className="h-4 w-4" />
                            <span>RESUME</span>
                        </>
                    ) : (
                        <>
                            <Pause className="h-4 w-4" />
                            <span>Pause</span>
                        </>
                    )}
                </button>
            </div>

            {/* Floating toast - doesn't shift layout */}
            {feedback && (
                <div
                    className={`absolute -bottom-8 left-0 right-0 text-center text-[10px] py-1 px-2 rounded-md transition-opacity animate-in fade-in slide-in-from-bottom-1 duration-300 ${
                        feedback.type === 'success' ? 'text-green-400' : 'text-red-400'
                    }`}
                >
                    {feedback.message}
                </div>
            )}
        </div>
    )
}
