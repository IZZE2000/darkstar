import { useEffect } from 'react'
import { useBlocker } from 'react-router-dom'

export function useUnsavedChangesGuard(isDirty: boolean) {
    // Browser guard (refresh/close tab)
    useEffect(() => {
        const handler = (e: BeforeUnloadEvent) => {
            if (isDirty) {
                e.preventDefault()
                e.returnValue = ''
            }
        }
        if (isDirty) {
            window.addEventListener('beforeunload', handler)
        }
        return () => window.removeEventListener('beforeunload', handler)
    }, [isDirty])

    // Router guard (internal navigation)
    // Block if dirty and moving to a different path
    const blocker = useBlocker(({ currentLocation, nextLocation }) => {
        const shouldIgnore = (nextLocation.state as { ignoreUnsavedChangesGuard?: boolean })?.ignoreUnsavedChangesGuard
        if (shouldIgnore) return false

        return (
            isDirty && currentLocation.pathname + currentLocation.search !== nextLocation.pathname + nextLocation.search
        )
    })

    return blocker
}
