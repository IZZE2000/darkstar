import { BaseField } from './types'

export const shouldRenderField = (
    field: BaseField,
    fullForm: Record<string, string | boolean | number | undefined>,
): boolean => {
    if (field.disabled) return false

    if (field.showIf) {
        // Safe access in case fullForm values are undefined
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
