import React from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle } from 'lucide-react'

interface NavigationBlockerDialogProps {
    visible: boolean
    onStay: () => void
    onLeave: () => void
}

export const NavigationBlockerDialog: React.FC<NavigationBlockerDialogProps> = ({ visible, onStay, onLeave }) => {
    if (!visible) return null

    return createPortal(
        <AnimatePresence>
            {visible && (
                <motion.div
                    className="modal-overlay"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onStay}
                >
                    <motion.div
                        className="modal w-full max-w-sm"
                        initial={{ scale: 0.95, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.95, opacity: 0 }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex flex-col items-center text-center gap-4">
                            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-warn/20 text-warn">
                                <AlertTriangle size={24} />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-text">Unsaved Changes</h3>
                                <p className="text-sm text-muted mt-1">
                                    You have unsaved changes. Are you sure you want to leave without saving?
                                </p>
                            </div>
                            <div className="flex gap-3 w-full mt-2">
                                <button onClick={onStay} className="flex-1 btn btn-secondary btn-lg rounded-xl">
                                    Stay
                                </button>
                                <button onClick={onLeave} className="flex-1 btn btn-danger btn-lg rounded-xl">
                                    Discard & Leave
                                </button>
                            </div>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>,
        document.body,
    )
}
