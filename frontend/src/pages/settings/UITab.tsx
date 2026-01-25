import React from 'react'
// Api and ThemeInfo commented out - Accent Theme card is hidden
// import { Api, ThemeInfo } from '../../lib/api'
import Card from '../../components/Card'
import { useSettingsForm } from './hooks/useSettingsForm'
import { SettingsField } from './components/SettingsField'
import { uiFieldList, uiSections } from './types'
import { shouldRenderField } from './logic'
import { motion, AnimatePresence } from 'framer-motion'
import { AdditionalAdvancedNotice, GlobalAdvancedLockedNotice } from './components/AdvancedLockedNotice'

export const UITab: React.FC<{ advancedMode?: boolean }> = ({ advancedMode }) => {
    const { form, fieldErrors, loading, saving, statusMessage, handleChange, save } = useSettingsForm(uiFieldList)

    // Themes state commented out - Accent Theme card is hidden
    // const [themes, setThemes] = useState<ThemeInfo[]>([])

    // useEffect(() => {
    //     Api.theme().then((res) => setThemes(res.themes))
    // }, [])

    if (loading) {
        return <Card className="p-6 text-sm text-muted">Loading UI configuration…</Card>
    }

    const fieldVariants = {
        initial: { opacity: 0, y: -10, height: 0 },
        animate: { opacity: 1, y: 0, height: 'auto' },
        exit: { opacity: 0, y: -10, height: 0 },
    }

    // const currentThemeIdx = config?.ui?.theme_accent_index ?? 0
    const parseOverlayDefaults = (raw: string | undefined): Record<string, boolean> => {
        if (!raw) return {}
        try {
            // Try to parse as JSON first (new format)
            const parsed = JSON.parse(raw)
            if (typeof parsed === 'object' && parsed !== null) {
                return parsed as Record<string, boolean>
            }
        } catch {
            // Fallback: handle comma-separated string (legacy format)
            const obj: Record<string, boolean> = {}
            raw.split(',').forEach((k) => {
                const trimmed = k.trim().toLowerCase()
                if (trimmed) obj[trimmed] = true
            })
            return obj
        }
        return {}
    }

    const overlayDefaults = parseOverlayDefaults(form['dashboard.overlay_defaults'])

    const toggleOverlay = (key: string) => {
        const next = { ...overlayDefaults, [key]: !overlayDefaults[key] }
        handleChange('dashboard.overlay_defaults', JSON.stringify(next))
    }

    const hasHiddenSections = uiSections.some((s) => s.fields.every((f) => f.isAdvanced))

    return (
        <div className="space-y-4">
            {/* Accent Theme Card - Hidden as per user request */}
            {/* ... */}

            {uiSections.map((section) => {
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
                                            Interface
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
                                    {section.title === 'Dashboard Defaults' && (
                                        <div className="mt-6 border-t border-line/30 pt-4">
                                            <div className="text-[10px] uppercase tracking-widest text-muted font-bold mb-3">
                                                Overlay Defaults
                                            </div>
                                            <div className="flex flex-wrap gap-2">
                                                {['solar', 'battery', 'load', 'grid', 'water', 'forecast'].map(
                                                    (key) => (
                                                        <button
                                                            key={key}
                                                            onClick={() => toggleOverlay(key)}
                                                            className={`rounded-lg px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider transition ${
                                                                overlayDefaults[key]
                                                                    ? 'bg-accent/20 text-accent border border-accent/30'
                                                                    : 'bg-surface2 text-muted border border-line/50 hover:border-line'
                                                            }`}
                                                        >
                                                            {key}
                                                        </button>
                                                    ),
                                                )}
                                            </div>
                                        </div>
                                    )}
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
                    {saving ? 'Saving…' : 'Save UI Settings'}
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
