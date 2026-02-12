import { useState, useEffect, useCallback, useMemo } from 'react'
import { Api, ConfigResponse } from '../../../lib/api'
import { useToast } from '../../../lib/useToast'
import { BaseField, InverterProfile } from '../types'
import { buildFormState, buildPatch } from '../utils'

// Standard keys that live directly in the inverter config (not in custom_entities)
const standardInverterKeys = new Set([
    'work_mode',
    'soc_target',
    'grid_charging_enable',
    'grid_charge_power',
    'minimum_reserve',
    'grid_max_export_power',
    'grid_max_export_power_switch',
    'max_charge_current',
    'max_discharge_current',
    'max_charge_power',
    'max_discharge_power',
])

export interface UseSettingsFormReturn {
    config: ConfigResponse | null
    form: Record<string, string>
    fieldErrors: Record<string, string>
    loading: boolean
    saving: boolean
    statusMessage: string | null
    isDirty: boolean
    haEntities: { entity_id: string; friendly_name: string; domain: string }[]
    haLoading: boolean
    handleChange: (key: string, value: string) => void
    save: (extraPatch?: Record<string, unknown>) => Promise<boolean>
    reset: () => void
    reload: () => Promise<void>
    reloadEntities: () => Promise<void>
}

export function useSettingsForm(baseFields: BaseField[], profiles: InverterProfile[] = []): UseSettingsFormReturn {
    const { toast } = useToast()
    const [config, setConfig] = useState<ConfigResponse | null>(null)
    const [form, setForm] = useState<Record<string, string>>({})
    const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
    const [loading, setLoading] = useState(true)
    const [formInitialized, setFormInitialized] = useState(false)
    const [saving, setSaving] = useState(false)
    const [statusMessage, setStatusMessage] = useState<string | null>(null)
    const [haEntities, setHaEntities] = useState<{ entity_id: string; friendly_name: string; domain: string }[]>([])
    const [haLoading, setHaLoading] = useState(false)

    // Compute dynamic field list including profile-specific entity fields
    // This uses the config data to determine which profile fields to include
    const fields = useMemo(() => {
        if (!config || profiles.length === 0) {
            return baseFields
        }

        // Get profile name from config
        const profileName = (config as unknown as Record<string, unknown>).system?.inverter_profile
        const selectedProfile = profiles.find((p) => p.name === profileName)

        if (!selectedProfile || !selectedProfile.entities) {
            return baseFields
        }

        const dynamicFields = [...baseFields]

        // Add required entity fields
        const requiredFields: BaseField[] = Object.keys(selectedProfile.entities.required || {}).map((key) => {
            const isStandard = standardInverterKeys.has(key)
            const label = key
                .split('_')
                .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ')

            return {
                key: isStandard ? `executor.inverter.${key}` : `executor.inverter.custom_entities.${key}`,
                label: `${label} Entity`,
                path: isStandard ? ['executor', 'inverter', key] : ['executor', 'inverter', 'custom_entities', key],
                type: 'entity',
                required: true,
                subsection: 'Inverter Profile Entities',
                helper: `Profile suggested mapping: ${selectedProfile.entities.required![key]}`,
            }
        })

        // Add optional entity fields
        const optionalFields: BaseField[] = Object.keys(selectedProfile.entities.optional || {}).map((key) => {
            const isStandard = standardInverterKeys.has(key)
            const label = key
                .split('_')
                .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ')

            return {
                key: isStandard ? `executor.inverter.${key}` : `executor.inverter.custom_entities.${key}`,
                label: `${label} Entity`,
                path: isStandard ? ['executor', 'inverter', key] : ['executor', 'inverter', 'custom_entities', key],
                type: 'entity',
                required: false,
                subsection: 'Inverter Profile Entities',
                helper: `Profile suggested mapping: ${selectedProfile.entities.optional![key]}`,
            }
        })

        // Filter out duplicates
        const existingKeys = new Set(dynamicFields.map((f) => f.key))
        const uniqueRequired = requiredFields.filter((f) => !existingKeys.has(f.key))
        const uniqueOptional = optionalFields.filter((f) => !existingKeys.has(f.key))

        dynamicFields.push(...uniqueRequired, ...uniqueOptional)

        return dynamicFields
    }, [config, profiles, baseFields])

    const reload = useCallback(async () => {
        setLoading(true)
        setStatusMessage(null)
        try {
            const cfg = await Api.config()
            setConfig(cfg)
            // Form will be rebuilt by the fields useMemo effect below
        } catch (err: unknown) {
            console.error('Failed to load configuration', err)
            setStatusMessage('Failed to load configuration: ' + (err instanceof Error ? err.message : 'Unknown error'))
        } finally {
            setLoading(false)
        }
    }, [])

    const reloadEntities = useCallback(async () => {
        setHaLoading(true)
        try {
            const data = await Api.haEntities()
            setHaEntities(data.entities || [])
        } catch (e) {
            console.error('Failed to load HA entities', e)
        } finally {
            setHaLoading(false)
        }
    }, [])

    useEffect(() => {
        reload()
        reloadEntities()
    }, [reload, reloadEntities])

    // Rebuild form state when fields change (for dynamic profile fields)
    useEffect(() => {
        if (config && fields.length > 0) {
            setForm(buildFormState(config as unknown as Record<string, unknown>, fields))
            setFieldErrors({})
            setFormInitialized(true)
        }
    }, [fields, config])

    const validateField = useCallback(
        (key: string, value: string, currentForm: Record<string, string>) => {
            const errors: Record<string, string> = {}
            const trimmed = value.trim()
            const field = fields.find((f) => f.key === key)

            if (!field) return errors

            // DEBUG: Log all validation attempts for battery_soc
            if (key.includes('battery_soc')) {
                console.warn('[SETTINGS_DEBUG] Validating battery_soc:', {
                    key,
                    value,
                    trimmed,
                    fieldType: field.type,
                    fieldLabel: field.label,
                    fullField: field,
                })
            }

            // Required check
            if (trimmed === '' && (field.required || key.includes('power_kw') || key.includes('capacity_kwh'))) {
                errors[key] = 'Required'
                return errors
            }

            // Only apply numeric validation if the field type is numeric
            if (field.type === 'number' || field.type === 'azimuth' || field.type === 'tilt') {
                // DEBUG: Log when entering numeric validation block
                if (key.includes('battery_soc')) {
                    console.error(
                        '[SETTINGS_DEBUG] ERROR: battery_soc entered numeric validation block! Type:',
                        field.type,
                    )
                }
                const num = Number(trimmed)
                if (trimmed !== '' && Number.isNaN(num)) {
                    errors[key] = 'Must be a number'
                } else if (!Number.isNaN(num)) {
                    if (key.includes('percent') || key.includes('soc')) {
                        if (num < 0 || num > 100) {
                            errors[key] = 'Must be between 0 and 100'
                        }
                    } else if (key.includes('power_kw') || key.includes('sek') || key.includes('kwh')) {
                        if (num < 0) {
                            errors[key] = 'Must be positive'
                        }
                    }
                }
            }

            // Cross-field validation for SoC
            const minKey = 'battery.min_soc_percent'
            const maxKey = 'battery.max_soc_percent'
            if (key === minKey || key === maxKey) {
                const minVal = Number(key === minKey ? trimmed : currentForm[minKey])
                const maxVal = Number(key === maxKey ? trimmed : currentForm[maxKey])
                if (!Number.isNaN(minVal) && !Number.isNaN(maxVal)) {
                    if (minVal >= maxVal) {
                        errors[minKey] = 'Min SoC must be less than max SoC'
                        errors[maxKey] = 'Max SoC must be greater than min SoC'
                    }
                }
            }

            return errors
        },
        [fields],
    )

    const handleChange = useCallback(
        (key: string, value: string) => {
            setForm((prev) => {
                const next = { ...prev, [key]: value }
                const newErrors = validateField(key, value, next)
                setFieldErrors((errs) => {
                    const updated = { ...errs, ...newErrors }
                    if (!newErrors[key]) delete updated[key]
                    // If it was a min/max SoC check, we might have cleared the other one too
                    if (key === 'battery.min_soc_percent' && !newErrors['battery.min_soc_percent'])
                        delete updated['battery.max_soc_percent']
                    if (key === 'battery.max_soc_percent' && !newErrors['battery.max_soc_percent'])
                        delete updated['battery.min_soc_percent']
                    return updated
                })
                return next
            })
            setStatusMessage(null)
        },
        [validateField],
    )

    const reset = useCallback(() => {
        if (config) {
            setForm(buildFormState(config as unknown as Record<string, unknown>, fields))
            setFieldErrors({})
            setStatusMessage(null)
            setFormInitialized(true)
        }
    }, [config, fields])

    const save = useCallback(
        async (extraPatch?: Record<string, unknown>) => {
            if (!config) return false
            if (Object.keys(fieldErrors).length > 0) {
                setStatusMessage('Please fix validation errors before saving.')
                return false
            }

            const patch = {
                ...buildPatch(config as unknown as Record<string, unknown>, form, fields),
                ...extraPatch,
            }
            console.warn('[CONFIG_SAVE] Generated patch:', patch)

            if (Object.keys(patch).length === 0) {
                setStatusMessage('No changes detected.')
                return false
            }

            setSaving(true)
            setStatusMessage(null)
            try {
                const result = await Api.configSave(patch as Record<string, unknown>)
                if (result.status === 'success') {
                    // REV LCL01: Show warnings if any exist
                    if (result.warnings && result.warnings.length > 0) {
                        result.warnings.forEach((w) => {
                            toast({
                                message: w.message,
                                description: w.guidance,
                                variant: 'warning',
                            })
                        })
                    } else {
                        toast({ message: 'Settings saved successfully', variant: 'success' })
                    }
                    await reload()
                    return true
                } else {
                    const apiErrors: Record<string, string> = {}
                    result.errors?.forEach((err) => {
                        if (err.field) apiErrors[err.field] = err.message
                    })
                    setFieldErrors((prev) => ({ ...prev, ...apiErrors }))
                    setStatusMessage(result.errors?.[0]?.message || 'Save failed')
                    toast({ message: 'Save failed', variant: 'error' })
                }
            } catch (err: unknown) {
                console.error('Save failed', err)
                // REV LCL01: Show actual error message from config validation
                const errMsg = err instanceof Error ? err.message : 'Unknown error'
                setStatusMessage(errMsg)
                toast({
                    message: 'Save failed',
                    description: errMsg,
                    variant: 'error',
                })
            } finally {
                setSaving(false)
            }
            return false
        },
        [config, form, fields, fieldErrors, reload, toast],
    )

    const isDirty = useMemo(() => {
        if (!config || !formInitialized) return false
        const patch = buildPatch(config as unknown as Record<string, unknown>, form, fields)
        return Object.keys(patch).length > 0
    }, [config, form, fields, formInitialized])

    return {
        config,
        form,
        fieldErrors,
        loading,
        saving,
        statusMessage,
        isDirty,
        haEntities,
        haLoading,
        handleChange,
        save,
        reset,
        reload,
        reloadEntities,
    }
}
