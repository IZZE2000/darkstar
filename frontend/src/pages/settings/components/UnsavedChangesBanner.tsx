import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Save, AlertTriangle } from 'lucide-react'
import { Banner } from '../../../components/ui/Banner'

interface UnsavedChangesBannerProps {
    visible: boolean
    onSave: () => void
    saving?: boolean
}

export const UnsavedChangesBanner: React.FC<UnsavedChangesBannerProps> = ({ visible, onSave, saving }) => {
    return (
        <AnimatePresence>
            {visible && (
                <motion.div
                    initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                    animate={{ opacity: 1, height: 'auto', marginBottom: 16 }}
                    exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                    transition={{ duration: 0.2 }}
                    className="sticky top-0 z-40 w-full"
                >
                    <Banner variant="warning" className="flex items-center justify-between shadow-lg border-warn/30">
                        <div className="flex items-center gap-3">
                            <AlertTriangle size={18} className="text-warn shrink-0" />
                            <div className="flex flex-col md:flex-row md:items-center md:gap-2">
                                <span className="text-sm font-semibold text-text">Unsaved Changes</span>
                                <span className="hidden md:inline text-muted">•</span>
                                <span className="text-xs text-muted">You have unsaved changes that will be lost.</span>
                            </div>
                        </div>
                        <button
                            onClick={onSave}
                            disabled={saving}
                            className="btn btn-primary btn-sm whitespace-nowrap text-xs py-1.5 px-3 rounded-lg shadow-sm"
                        >
                            {saving ? (
                                'Saving...'
                            ) : (
                                <>
                                    <Save size={14} />
                                    Save Changes
                                </>
                            )}
                        </button>
                    </Banner>
                </motion.div>
            )}
        </AnimatePresence>
    )
}
