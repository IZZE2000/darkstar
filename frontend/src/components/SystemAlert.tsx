/**
 * SystemAlert Component
 *
 * Displays critical and warning banners at the top of the app
 * when system health issues are detected.
 *
 * Styles are in index.css under @layer components.
 */

import React, { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { PlannerErrorDetails } from './PlannerErrorDetails'

export interface HealthIssue {
    category: string
    severity: 'critical' | 'warning' | 'info'
    message: string
    guidance: string
    entity_id?: string | null
    code?: string | null
    details?: Record<string, unknown> | null
    retry_in_s?: number | null
}

export interface HealthStatus {
    healthy: boolean
    issues: HealthIssue[]
    checked_at: string
    critical_count: number
    warning_count: number
}

interface SystemAlertProps {
    health: HealthStatus | null
    onDismiss?: () => void
}

export function SystemAlert({ health, onDismiss }: SystemAlertProps) {
    const [selectedIssue, setSelectedIssue] = useState<HealthIssue | null>(null)
    const [collapsed, setCollapsed] = useState(false)

    if (!health || health.healthy) {
        return null
    }

    const criticalIssues = health.issues.filter((i) => i.severity === 'critical')
    const warningIssues = health.issues.filter((i) => i.severity === 'warning')
    const allIssues = [...criticalIssues, ...warningIssues]

    return (
        <div className="space-y-2">
            {/* Collapsed indicator */}
            {collapsed ? (
                <div className="flex items-center gap-2">
                    {allIssues.map((issue, idx) => (
                        <button
                            key={`indicator-${idx}`}
                            onClick={() => setCollapsed(false)}
                            className={`inline-flex items-center gap-1.5 text-[10px] px-2 py-1 rounded-md cursor-pointer transition-colors ${
                                issue.severity === 'critical'
                                    ? 'bg-bad/20 text-bad hover:bg-bad/30'
                                    : 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30'
                            }`}
                        >
                            <span>⚠️</span>
                            <code className="font-mono">{issue.code || issue.category}</code>
                            <ChevronDown className="h-3 w-3" />
                        </button>
                    ))}
                </div>
            ) : (
                <>
                    {/* Critical Errors */}
                    {criticalIssues.map((issue, idx) => (
                        <div
                            key={`critical-${idx}`}
                            className="banner banner-error px-4 py-3 flex items-center justify-between"
                        >
                            <div className="flex items-center gap-2">
                                <span>⚠️</span>
                                <span className="font-medium">{issue.message}</span>
                                {issue.entity_id && (
                                    <code className="text-[10px] bg-white/20 px-1.5 py-0.5 rounded">
                                        {issue.entity_id}
                                    </code>
                                )}
                                <span className="opacity-70 text-xs">— {issue.guidance}</span>
                                {issue.details && (
                                    <button
                                        onClick={() => setSelectedIssue(issue)}
                                        className="text-[10px] px-2 py-0.5 rounded bg-white/20 hover:bg-white/30 transition-colors"
                                    >
                                        View details
                                    </button>
                                )}
                            </div>
                            <div className="flex items-center gap-1">
                                {onDismiss && (
                                    <button
                                        onClick={onDismiss}
                                        className="opacity-60 hover:opacity-100 text-xs px-2 py-1"
                                        title="Dismiss"
                                    >
                                        ✕
                                    </button>
                                )}
                                <button
                                    onClick={() => setCollapsed(true)}
                                    className="opacity-60 hover:opacity-100 text-xs px-1 py-1"
                                    title="Collapse"
                                >
                                    <ChevronUp className="h-3.5 w-3.5" />
                                </button>
                            </div>
                        </div>
                    ))}

                    {/* Warnings */}
                    {warningIssues.map((issue, idx) => (
                        <div
                            key={`warning-${idx}`}
                            className="banner banner-warning px-4 py-3 flex items-center justify-between"
                        >
                            <div className="flex items-center gap-2">
                                <span>⚡</span>
                                <span className="font-medium">{issue.message}</span>
                                <span className="opacity-70 text-xs ml-2">— {issue.guidance}</span>
                                {issue.details && (
                                    <button
                                        onClick={() => setSelectedIssue(issue)}
                                        className="text-[10px] px-2 py-0.5 rounded bg-white/20 hover:bg-white/30 transition-colors"
                                    >
                                        View details
                                    </button>
                                )}
                            </div>
                            <button
                                onClick={() => setCollapsed(true)}
                                className="opacity-60 hover:opacity-100 text-xs px-1 py-1"
                                title="Collapse"
                            >
                                <ChevronUp className="h-3.5 w-3.5" />
                            </button>
                        </div>
                    ))}
                </>
            )}

            {/* Details drawer */}
            {selectedIssue && (
                <PlannerErrorDetails
                    issue={selectedIssue}
                    open={!!selectedIssue}
                    onClose={() => setSelectedIssue(null)}
                />
            )}
        </div>
    )
}

export default SystemAlert
