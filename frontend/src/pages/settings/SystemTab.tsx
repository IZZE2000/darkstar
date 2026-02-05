import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Api } from '../../lib/api'
import Card from '../../components/Card'
import { useSettingsForm } from './hooks/useSettingsForm'
import { SettingsField } from './components/SettingsField'
import { systemFieldList, systemSections } from './types'
import { shouldRenderField } from './logic'
import { motion, AnimatePresence } from 'framer-motion'
import { AdditionalAdvancedNotice, GlobalAdvancedLockedNotice } from './components/AdvancedLockedNotice'
import { UnsavedChangesBanner } from './components/UnsavedChangesBanner'
import { NavigationBlockerDialog } from './components/NavigationBlockerDialog'
import { useUnsavedChangesGuard } from './hooks/useUnsavedChangesGuard'
import { ProfileSetupHelper } from './components/ProfileSetupHelper'

export const SystemTab: React.FC<{ advancedMode?: boolean }> = ({ advancedMode }) => {
    const navigate = useNavigate()
    const {
        form,
        fieldErrors,
        loading,
        saving,
        statusMessage,
        haEntities,
        haLoading,
        handleChange,
        save,
        reloadEntities,
        isDirty,
    } = useSettingsForm(systemFieldList)

    const blocker = useUnsavedChangesGuard(isDirty)

    const [haTestStatus, setHaTestStatus] = useState<string | null>(null)

    const profile = form['system.inverter_profile']
    const unit = form['executor.inverter.control_unit']

    useEffect(() => {
        if (profile === 'deye' && unit !== 'A') {
            handleChange('executor.inverter.control_unit', 'A')
        }
    }, [profile, unit, handleChange])

    const handleApplySuggestions = (suggestions: Record<string, unknown>) => {
        Object.entries(suggestions).forEach(([key, value]) => {
            handleChange(key, String(value))
        })
    }

    const handleTestConnection = async () => {
        setHaTestStatus('Testing...')
        try {
            const url = form['home_assistant.url']
            const token = form['home_assistant.token']
            const data = await Api.haTest({ url, token })

            if (data.success) {
                setHaTestStatus('Success: Connected!')
                reloadEntities()
            } else {
                setHaTestStatus(`Error: ${data.message}`)
            }
        } catch (e: unknown) {
            setHaTestStatus(`Error: ${e instanceof Error ? e.message : 'Unknown error'}`)
        }
    }

    if (loading) {
        return <Card className="p-6 text-sm text-muted">Loading system configuration…</Card>
    }

    const fieldVariants = {
        initial: { opacity: 0, y: -10, height: 0 },
        animate: { opacity: 1, y: 0, height: 'auto' },
        exit: { opacity: 0, y: -10, height: 0 },
    }

    const hasHiddenSections = systemSections.some((s) => s.fields.every((f) => f.isAdvanced))

    return (
        <div className="space-y-4">
            <UnsavedChangesBanner visible={isDirty} onSave={() => save()} saving={saving} />

            <ProfileSetupHelper profileName={profile} onApply={handleApplySuggestions} />

            {/* HA Add-on Guidance Banner */}

            {systemSections.map((section, idx) => {
                const prevSection = idx > 0 ? systemSections[idx - 1] : null
                const showDivider = section.isHA && prevSection && !prevSection.isHA

                // Group fields by subsection
                const groups: Record<string, typeof section.fields> = {}
                const order: string[] = []

                section.fields.forEach((f) => {
                    const sub = f.subsection || 'default'
                    if (!groups[sub]) {
                        groups[sub] = []
                        order.push(sub)
                    }
                    groups[sub].push(f)
                })
                const params = { groups, order }

                const isEntirelyAdvanced = section.fields.every((f) => f.isAdvanced)
                const shouldShowCard = advancedMode || !isEntirelyAdvanced

                return (
                    <AnimatePresence key={section.title} initial={false}>
                        {shouldShowCard && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                transition={{ duration: 0.3 }}
                                className="overflow-hidden"
                            >
                                <div key={section.title}>
                                    {showDivider && (
                                        <div className="py-8 flex items-center gap-4">
                                            <div className="h-px flex-1 bg-line/30" />
                                            <span className="text-[11px] font-bold uppercase tracking-[0.2em] text-muted whitespace-nowrap">
                                                Home Assistant Integration
                                            </span>
                                            <div className="h-px flex-1 bg-line/30" />
                                        </div>
                                    )}
                                    {section.title === 'Home Assistant Connection' && (
                                        <Card className="mb-4 p-4 bg-accent/5 border border-accent/20">
                                            <div className="flex items-start gap-3">
                                                <div className="text-xl">🔌</div>
                                                <div>
                                                    <div className="text-sm font-semibold text-accent">
                                                        HA Add-on User?
                                                    </div>
                                                    <p className="text-xs text-muted mt-1 leading-relaxed">
                                                        If you are running as a Home Assistant Add-on, connection
                                                        settings are managed automatically.
                                                        <strong>
                                                            {' '}
                                                            Manually entering them here is not required
                                                        </strong>{' '}
                                                        and they will be reset to match your add-on configuration on
                                                        next save.
                                                    </p>
                                                </div>
                                            </div>
                                        </Card>
                                    )}
                                    <Card className="p-6">
                                        <div className="flex items-baseline justify-between gap-2">
                                            <div>
                                                <div className="text-base font-bold text-text">{section.title}</div>
                                                <p className="text-xs text-muted mt-1">{section.description}</p>
                                            </div>
                                            <span className="text-[10px] uppercase text-muted tracking-wide">
                                                System
                                            </span>
                                        </div>
                                        <div className="mt-5 grid gap-4 sm:grid-cols-2">
                                            {params.order.map((subKey) => {
                                                const isSubEntirelyAdvanced = params.groups[subKey].every(
                                                    (f) => f.isAdvanced,
                                                )
                                                const shouldShowSub = advancedMode || !isSubEntirelyAdvanced

                                                return (
                                                    <AnimatePresence key={subKey} initial={false}>
                                                        {shouldShowSub && (
                                                            <motion.div
                                                                initial={{ opacity: 0, height: 0 }}
                                                                animate={{ opacity: 1, height: 'auto' }}
                                                                exit={{ opacity: 0, height: 0 }}
                                                                transition={{ duration: 0.3 }}
                                                                className="col-span-2 overflow-hidden"
                                                            >
                                                                {subKey !== 'default' ? (
                                                                    <Card className="p-4 bg-surface1 border border-line/20 rounded-xl mb-4">
                                                                        <div className="text-sm font-semibold text-muted mb-3 uppercase tracking-wider">
                                                                            {subKey}
                                                                        </div>
                                                                        <div className="grid gap-4 sm:grid-cols-2">
                                                                            <AnimatePresence initial={false}>
                                                                                {params.groups[subKey].map(
                                                                                    (field) =>
                                                                                        (advancedMode ||
                                                                                            !field.isAdvanced) &&
                                                                                        shouldRenderField(
                                                                                            field,
                                                                                            form,
                                                                                        ) && (
                                                                                            <motion.div
                                                                                                key={field.key}
                                                                                                variants={fieldVariants}
                                                                                                initial="initial"
                                                                                                animate="animate"
                                                                                                exit="exit"
                                                                                                transition={{
                                                                                                    duration: 0.2,
                                                                                                    ease: 'easeOut',
                                                                                                }}
                                                                                                className="overflow-hidden"
                                                                                            >
                                                                                                <SettingsField
                                                                                                    field={field}
                                                                                                    value={
                                                                                                        form[
                                                                                                            field.key
                                                                                                        ] ?? ''
                                                                                                    }
                                                                                                    onChange={
                                                                                                        handleChange
                                                                                                    }
                                                                                                    error={
                                                                                                        fieldErrors[
                                                                                                            field.key
                                                                                                        ]
                                                                                                    }
                                                                                                    haEntities={
                                                                                                        haEntities
                                                                                                    }
                                                                                                    haLoading={
                                                                                                        haLoading
                                                                                                    }
                                                                                                    fullForm={form}
                                                                                                />
                                                                                            </motion.div>
                                                                                        ),
                                                                                )}

                                                                                {!advancedMode &&
                                                                                    params.groups[subKey].some(
                                                                                        (f) => f.isAdvanced,
                                                                                    ) &&
                                                                                    params.groups[subKey].some(
                                                                                        (f) => !f.isAdvanced,
                                                                                    ) && (
                                                                                        <motion.div
                                                                                            key={`${subKey}-additional`}
                                                                                            variants={fieldVariants}
                                                                                            initial="initial"
                                                                                            animate="animate"
                                                                                            exit="exit"
                                                                                            className="col-span-2 overflow-hidden"
                                                                                        >
                                                                                            <AdditionalAdvancedNotice />
                                                                                        </motion.div>
                                                                                    )}
                                                                            </AnimatePresence>
                                                                        </div>
                                                                    </Card>
                                                                ) : (
                                                                    <div className="grid gap-4 sm:grid-cols-2 mb-4">
                                                                        <AnimatePresence initial={false}>
                                                                            {params.groups[subKey].map(
                                                                                (field) =>
                                                                                    (advancedMode ||
                                                                                        !field.isAdvanced) &&
                                                                                    shouldRenderField(field, form) && (
                                                                                        <motion.div
                                                                                            key={field.key}
                                                                                            variants={fieldVariants}
                                                                                            initial="initial"
                                                                                            animate="animate"
                                                                                            exit="exit"
                                                                                            transition={{
                                                                                                duration: 0.2,
                                                                                                ease: 'easeOut',
                                                                                            }}
                                                                                            className="overflow-hidden"
                                                                                        >
                                                                                            <SettingsField
                                                                                                field={field}
                                                                                                value={
                                                                                                    form[field.key] ??
                                                                                                    ''
                                                                                                }
                                                                                                onChange={handleChange}
                                                                                                error={
                                                                                                    fieldErrors[
                                                                                                        field.key
                                                                                                    ]
                                                                                                }
                                                                                                haEntities={haEntities}
                                                                                                haLoading={haLoading}
                                                                                                fullForm={form}
                                                                                            />
                                                                                        </motion.div>
                                                                                    ),
                                                                            )}
                                                                            {!advancedMode &&
                                                                                params.groups[subKey].some(
                                                                                    (f) => f.isAdvanced,
                                                                                ) &&
                                                                                params.groups[subKey].some(
                                                                                    (f) => !f.isAdvanced,
                                                                                ) && (
                                                                                    <motion.div
                                                                                        key={`${subKey}-additional`}
                                                                                        variants={fieldVariants}
                                                                                        initial="initial"
                                                                                        animate="animate"
                                                                                        exit="exit"
                                                                                        className="col-span-2 overflow-hidden"
                                                                                    >
                                                                                        <AdditionalAdvancedNotice />
                                                                                    </motion.div>
                                                                                )}
                                                                        </AnimatePresence>
                                                                    </div>
                                                                )}
                                                            </motion.div>
                                                        )}
                                                    </AnimatePresence>
                                                )
                                            })}
                                        </div>
                                        {section.title === 'Home Assistant Connection' && (
                                            <div className="mt-4 flex items-center gap-3">
                                                <button
                                                    type="button"
                                                    onClick={handleTestConnection}
                                                    className="rounded-xl px-4 py-2 text-[11px] font-semibold bg-neutral hover:bg-neutral/80 text-white transition"
                                                >
                                                    {haTestStatus && haTestStatus.startsWith('Testing')
                                                        ? 'Testing...'
                                                        : 'Test Connection'}
                                                </button>
                                                {haTestStatus && (
                                                    <span
                                                        className={`text-xs ${haTestStatus.startsWith('Success') ? 'text-good' : 'text-bad'}`}
                                                    >
                                                        {haTestStatus}
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </Card>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                )
            })}

            {!advancedMode && hasHiddenSections && <GlobalAdvancedLockedNotice />}

            <div className="flex flex-wrap items-center gap-3">
                <button
                    disabled={saving}
                    onClick={() => save()}
                    className="flex items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-[11px] font-semibold transition btn-glow-primary bg-accent hover:bg-accent2 text-[#100f0e] disabled:opacity-50"
                >
                    {saving ? 'Saving…' : 'Save System Settings'}
                </button>
                {statusMessage && (
                    <div
                        className={`rounded-lg p-3 text-sm ${
                            statusMessage.startsWith('Please fix') ||
                            statusMessage.startsWith('Save failed') ||
                            statusMessage.startsWith('Failed to load')
                                ? 'bg-bad/10 border border-bad/30 text-bad'
                                : 'bg-good/10 border border-good/30 text-good'
                        }`}
                    >
                        {statusMessage}
                    </div>
                )}
            </div>

            <NavigationBlockerDialog
                visible={blocker.state === 'blocked'}
                onStay={() => blocker.reset?.()}
                onLeave={() => {
                    if (blocker.location) {
                        navigate(blocker.location.pathname + blocker.location.search, {
                            state: { ...blocker.location.state, ignoreUnsavedChangesGuard: true },
                        })
                    }
                }}
            />
        </div>
    )
}
