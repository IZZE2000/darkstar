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

export const AdditionalAdvancedNotice: React.FC = () => (
    <div className="col-span-2 pt-2 border-t border-line/5 mt-1 flex items-center gap-2 text-[9px] text-muted/60 font-bold uppercase tracking-[0.15em]">
        <ShieldAlert size={10} className="text-bad/50" />
        <span>Additional tuning available in Advanced Mode</span>
    </div>
)
