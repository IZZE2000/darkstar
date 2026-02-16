import { BaseField } from './types'

export const shouldRenderField = (
    field: BaseField,
    fullForm: Record<string, string | boolean | number | undefined>,
    config?: Record<string, unknown>,
): boolean => {
    if (field.disabled) return false

    if (field.showIf) {
        // For system.* showIf checks, use config if available (form may not have system fields)
        if (field.showIf.configKey.startsWith('system.') && config) {
            const systemKey = field.showIf.configKey.replace('system.', '')
            const configValue = (config as unknown as { system?: Record<string, unknown> })?.system?.[systemKey]
            const expectedVal = field.showIf.value ?? true

            if (typeof expectedVal === 'boolean') {
                return configValue === expectedVal
            }

            if (Array.isArray(expectedVal)) {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                return expectedVal.includes(configValue as any) || expectedVal.some((v) => v === configValue)
            }

            return configValue === expectedVal
        }

        // Standard form-based check
        const currentVal = fullForm[field.showIf.configKey]
        const expectedVal = field.showIf.value ?? true

        // If expectedVal is a boolean, treat currentVal as a boolean string ('true'/'false')
        if (typeof expectedVal === 'boolean') {
            return (currentVal === 'true') === expectedVal
        }

        // Support array of valid values (OR logic)
        if (Array.isArray(expectedVal)) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return expectedVal.includes(currentVal as any) || expectedVal.some((v) => String(v) === currentVal)
        }

        // Otherwise, do a direct string comparison
        return currentVal === expectedVal
    }

    if (field.showIfAll) {
        return field.showIfAll.every((k) => fullForm[k] === 'true')
    }

    if (field.showIfAny) {
        return field.showIfAny.some((k) => fullForm[k] === 'true')
    }

    return true
}
