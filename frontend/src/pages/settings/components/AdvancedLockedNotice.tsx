import React from 'react'
import { ShieldAlert } from 'lucide-react'

export const AdvancedLockedNotice: React.FC = () => (
    <div className="col-span-2 flex items-center gap-3 py-3 px-4 border border-dashed border-line/30 rounded-xl bg-surface2/20 animate-in fade-in duration-500">
        <div className="flex-shrink-0 flex items-center justify-center w-7 h-7 rounded-lg bg-surface3 text-muted">
            <ShieldAlert size={14} />
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3 flex-1">
            <span className="text-[11px] font-bold text-text uppercase tracking-wider">Advanced Tuning Locked</span>
            <span className="hidden sm:block h-3 w-px bg-line/30" />
            <span className="text-[10px] text-muted">
                Enable Advanced Mode in the settings header to unlock these parameters.
            </span>
        </div>
    </div>
)

export const AdditionalAdvancedNotice: React.FC<{ visible?: boolean }> = ({ visible = true }) => {
    if (!visible) return null
    return (
        <div className="col-span-2 pt-2 border-t border-line/5 mt-1 flex items-center gap-2 text-[9px] text-muted/60 font-bold uppercase tracking-[0.15em]">
            <ShieldAlert size={10} className="text-bad/50" />
            <span>Additional tuning available in Advanced Mode</span>
        </div>
    )
}

export const GlobalAdvancedLockedNotice: React.FC = () => (
    <div className="flex items-center gap-4 py-8 px-8 border-2 border-dashed border-line/20 rounded-2xl bg-surface2/10 mt-4 animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div className="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-xl bg-surface3 border border-line/20 text-muted shadow-inner">
            <ShieldAlert size={22} className="text-muted/50" />
        </div>
        <div className="flex flex-col gap-1">
            <div className="text-xs font-bold text-text uppercase tracking-widest flex items-center gap-2">
                <span>Advanced Tuning Mode Required</span>
                <span className="h-1 w-1 rounded-full bg-bad/50 animate-pulse" />
            </div>
            <p className="text-[11px] text-muted/80 leading-relaxed max-w-md">
                Some technical configuration sections are hidden to keep your dashboard clean. Enable{' '}
                <span className="text-text font-semibold">Advanced Mode</span> in the header to unlock deep tuning
                parameters and experimental controls.
            </p>
        </div>
    </div>
)
