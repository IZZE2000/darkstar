import { useEffect, useState } from 'react'
import { Database, AlertTriangle, CheckCircle, RefreshCw, ServerOff } from 'lucide-react'
import Card from './Card'
import { Api } from '../lib/api'
import type { GapInfo } from '../lib/api'

export default function DataBackfillCard() {
    const [loading, setLoading] = useState(false)
    const [backfilling, setBackfilling] = useState(false)
    const [gaps, setGaps] = useState<GapInfo[]>([])
    const [error, setError] = useState<string | null>(null)
    const [successMsg, setSuccessMsg] = useState<string | null>(null)

    const fetchGaps = async () => {
        console.log('🔍 fetchGaps() called at:', new Date().toISOString())
        setLoading(true)
        setError(null)
        try {
            console.log('📡 About to call Api.learningGaps(10)...')
            const data = await Api.learningGaps(10)
            console.log('✅ API response received:', data)
            console.log('📊 Gaps count:', data.length)
            if (data.length > 0) console.log('📊 First gap:', data[0])
            setGaps(data)
            console.log('✅ State updated with gaps')
        } catch (err) {
            console.error('❌ API call failed:', err)
            console.error('❌ Error details:', JSON.stringify(err, null, 2))
            setError('Failed to detect gaps.')
        } finally {
            setLoading(false)
            console.log('✅ fetchGaps() completed')
        }
    }

    useEffect(() => {
        console.log('🚀 DataBackfillCard mounted, calling fetchGaps...')
        fetchGaps()
        // Auto-refresh every 5 minutes
        const interval = setInterval(() => {
            console.log('🔄 Auto-refresh triggered')
            fetchGaps()
        }, 5 * 60 * 1000)
        return () => {
            console.log('🛑 DataBackfillCard unmounting, clearing interval')
            clearInterval(interval)
        }
    }, [])

    const handleBackfill = async () => {
        setBackfilling(true)
        setSuccessMsg(null)
        setError(null)
        try {
            const res = await Api.learningBackfill()
            setSuccessMsg(res.message)
            // Poll for completion (naive approach for now, or just refresh gaps after a delay)
            // Ideally WS would push updates, but for now we just wait a bit and refresh gaps
            setTimeout(() => {
                fetchGaps()
                setBackfilling(false)
            }, 5000)
        } catch (err) {
            console.error('Failed to trigger backfill:', err)
            setError('Failed to start backfill.')
            setBackfilling(false)
        }
    }

    const totalMissing = gaps.reduce((acc, gap) => acc + gap.missing_slots, 0)
    const isHealthy = gaps.length === 0 && !error
    const hasError = !!error

    const testAPI = async () => {
        console.log('🧪 Testing API directly...')
        try {
            const response = await fetch('/api/learning/gaps?days=10')
            console.log('📡 Raw response status:', response.status)
            const data = await response.json()
            console.log('📊 Raw response data:', data)
        } catch (err) {
            console.error('❌ Direct API test failed:', err)
        }
    }

    return (
        <Card className="p-4 md:p-5 flex flex-col h-full min-h-0 overflow-hidden relative">
            <div className="flex items-center gap-2 mb-4 shrink-0">
                <Database className={`h-4 w-4 ${hasError ? 'text-red-400' : isHealthy ? 'text-emerald-400' : 'text-amber-400'}`} />
                <span className="text-xs font-medium text-text">Data Integrity</span>
                {/* DEBUG BUTTON */}
                <button onClick={testAPI} className="ml-auto text-[10px] bg-red-500/20 text-red-400 px-2 py-0.5 rounded hover:bg-red-500/30">
                    Test API
                </button>
            </div>

            <div className="flex-1 flex flex-col justify-center items-center gap-3">
                {loading && !backfilling && gaps.length === 0 ? (
                    <div className="text-[11px] text-muted animate-pulse">Scanning history...</div>
                ) : hasError ? (
                    <div className="flex flex-col items-center gap-1 text-center">
                        <ServerOff className="h-6 w-6 text-red-400 opacity-80" />
                        <span className="text-[11px] text-red-300">{error}</span>
                        <button
                            onClick={fetchGaps}
                            className="text-[10px] text-muted underline hover:text-text mt-1"
                        >
                            Retry
                        </button>
                    </div>
                ) : isHealthy ? (
                    <div className="flex flex-col items-center gap-1 text-center">
                        <div className="h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center mb-1">
                            <CheckCircle className="h-5 w-5 text-emerald-400" />
                        </div>
                        <span className="text-[11px] text-emerald-400 font-medium">System data up to date</span>
                        <span className="text-[10px] text-muted">No gaps in last 10 days</span>
                    </div>
                ) : (
                    <div className="flex flex-col items-center gap-2 text-center w-full">
                        <div className="h-10 w-10 rounded-full bg-amber-500/10 flex items-center justify-center mb-1 relative">
                            <AlertTriangle className="h-5 w-5 text-amber-400" />
                            <div className="absolute -top-1 -right-1 bg-surface border border-surface rounded-full">
                                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-[9px] font-bold text-[#0F1216]">
                                    {gaps.length}
                                </span>
                            </div>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-[11px] text-amber-400 font-medium">{totalMissing} Missing Slots</span>
                            <span className="text-[10px] text-muted">Detected across {gaps.length} ranges</span>
                        </div>

                        <div className="w-full mt-2 bg-surface2/50 rounded-lg p-2 max-h-24 overflow-y-auto custom-scrollbar text-left border border-white/5">
                            {gaps.map((gap, i) => (
                                <div key={i} className="flex justify-between items-center text-[9px] py-0.5 border-b border-white/5 last:border-0">
                                    <span className="text-muted font-mono">{new Date(gap.start_time).toLocaleDateString()}</span>
                                    <span className="text-amber-300/80">{gap.missing_slots} slots</span>
                                </div>
                            ))}
                        </div>

                        <button
                            onClick={handleBackfill}
                            disabled={backfilling}
                            className={`mt-2 w-full flex items-center justify-center gap-2 py-2 rounded-lg text-[11px] font-semibold transition-all ${backfilling
                                ? 'bg-amber-500/20 text-amber-400 cursor-not-allowed'
                                : 'bg-amber-500 hover:bg-amber-400 text-[#0F1216]'
                                }`}
                        >
                            {backfilling ? (
                                <>
                                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                                    <span>Syncing...</span>
                                </>
                            ) : (
                                <>
                                    <RefreshCw className="h-3.5 w-3.5" />
                                    <span>Fill Gaps via HA</span>
                                </>
                            )}
                        </button>
                        {successMsg && (
                            <span className="text-[9px] text-emerald-400 animate-fade-in mt-1">
                                {successMsg}
                            </span>
                        )}
                    </div>
                )}
            </div>
            {/* Background decoration */}
            <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                <Database className="h-24 w-24 transform rotate-12" />
            </div>
        </Card>
    )
}
