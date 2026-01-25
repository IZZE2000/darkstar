import React from 'react'
import Card from '../../components/Card'
import { useSettingsForm } from './hooks/useSettingsForm'
import { SettingsField } from './components/SettingsField'
import { parameterFieldList, parameterSections } from './types'
import { shouldRenderField } from './logic'
import { motion, AnimatePresence } from 'framer-motion'
import { AdditionalAdvancedNotice, GlobalAdvancedLockedNotice } from './components/AdvancedLockedNotice'

export const ParametersTab: React.FC<{ advancedMode?: boolean }> = ({ advancedMode }) => {
    const { form, fieldErrors, loading, saving, statusMessage, handleChange, save } =
        useSettingsForm(parameterFieldList)

    if (loading) {
        return <Card className="p-6 text-sm text-muted">Loading optimization parameters…</Card>
    }

    const fieldVariants = {
        initial: { opacity: 0, y: -10, height: 0 },
        animate: { opacity: 1, y: 0, height: 'auto' },
        exit: { opacity: 0, y: -10, height: 0 },
    }

    const hasHiddenSections = parameterSections.some((s) => s.fields.every((f) => f.isAdvanced))

    return (
        <div className="space-y-4">
            {parameterSections.map((section) => {
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
                                <Card className="p-6 mb-4">
                                    <div className="flex items-baseline justify-between gap-2">
                                        <div>
                                            <div className="text-sm font-semibold">{section.title}</div>
                                            <p className="text-xs text-muted mt-1">{section.description}</p>
                                        </div>
                                        <span className="text-[10px] uppercase text-muted tracking-wide">
                                            Optimization
                                        </span>
                                    </div>
                                    <div className="mt-5 grid gap-4 sm:grid-cols-2">
                                        <AnimatePresence initial={false}>
                                            {section.fields.map(
                                                (field) =>
                                                    (advancedMode || !field.isAdvanced) &&
                                                    shouldRenderField(field, form) && (
                                                        <motion.div
                                                            key={field.key}
                                                            variants={fieldVariants}
                                                            initial="initial"
                                                            animate="animate"
                                                            exit="exit"
                                                            transition={{ duration: 0.2, ease: 'easeOut' }}
                                                            className="overflow-hidden"
                                                        >
                                                            <SettingsField
                                                                field={field}
                                                                value={form[field.key] ?? ''}
                                                                onChange={handleChange}
                                                                error={fieldErrors[field.key]}
                                                                fullForm={form}
                                                            />
                                                        </motion.div>
                                                    ),
                                            )}

                                            {!advancedMode &&
                                                section.fields.some((f) => f.isAdvanced) &&
                                                section.fields.some((f) => !f.isAdvanced) && (
                                                    <motion.div
                                                        key={`${section.title}-additional`}
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
                    {saving ? 'Saving…' : 'Save Parameters'}
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
        </div>
    )
}
