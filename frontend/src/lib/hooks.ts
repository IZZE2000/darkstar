import { useEffect, useRef } from 'react'
import { getSocket } from './socket'

export const useSocket = (event: string, callback: (data: unknown) => void) => {
    // Store the latest callback in a ref so we don't have to re-subscribe on every render
    const callbackRef = useRef(callback)

    // Update ref when callback changes
    useEffect(() => {
        callbackRef.current = callback
    }, [callback])

    useEffect(() => {
        const socket = getSocket()

        // Use a stable wrapper function
        const handleEvent = (data: unknown) => {
            if (callbackRef.current) {
                callbackRef.current(data)
            }
        }

        socket.on(event, handleEvent)

        return () => {
            socket.off(event, handleEvent)
        }
    }, [event]) // Only re-subscribe if the event name itself changes
}
