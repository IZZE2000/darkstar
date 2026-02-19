import { useEffect, useState } from 'react'
import {
    createBrowserRouter,
    RouterProvider,
    Outlet,
    createRoutesFromElements,
    Route,
    Navigate,
} from 'react-router-dom'
import Sidebar from './components/Sidebar'
import ErrorBoundary from './components/ErrorBoundary'
import Dashboard from './pages/Dashboard'
import Debug from './pages/Debug'
import Settings from './pages/settings'
import Aurora from './pages/Aurora'
import Executor from './pages/Executor'
import DesignSystem from './pages/DesignSystem'
import PowerFlowLab from './pages/PowerFlowLab'
import ChartExamples from './pages/ChartExamples'
import { Api, HealthResponse, ConfigSaveResponse } from './lib/api'
import { SystemAlert } from './components/SystemAlert'
import { ToastProvider } from './components/ui/Toast'

function RootLayout() {
    const [backendOffline, setBackendOffline] = useState(false)
    const [healthStatus, setHealthStatus] = useState<HealthResponse | null>(null)
    const [configWarnings, setConfigWarnings] = useState<ConfigSaveResponse | null>(null)

    // Check config validation on mount
    useEffect(() => {
        Api.configValidate()
            .then(setConfigWarnings)
            .catch(() => setConfigWarnings(null))
    }, [])

    // REV UI23: Re-check config validation when config changes (after save)
    useEffect(() => {
        const handleConfigChanged = () => {
            Api.configValidate()
                .then(setConfigWarnings)
                .catch(() => setConfigWarnings(null))
        }
        window.addEventListener('config-changed', handleConfigChanged)
        return () => window.removeEventListener('config-changed', handleConfigChanged)
    }, [])

    useEffect(() => {
        let cancelled = false
        let errorCount = 0

        const checkHealth = async () => {
            try {
                // Check both status and health
                const [, health] = await Promise.all([Api.status(), Api.health()])
                if (cancelled) return
                errorCount = 0
                setBackendOffline(false)
                setHealthStatus(health)
            } catch {
                if (cancelled) return
                errorCount += 1
                if (errorCount >= 3) {
                    setBackendOffline(true)
                    // Clear health status when backend is offline
                    setHealthStatus(null)
                }
            }
        }

        checkHealth()
        // Check every 60 seconds
        const id = window.setInterval(checkHealth, 60000)

        return () => {
            cancelled = true
            window.clearInterval(id)
        }
    }, [])

    return (
        <>
            <Sidebar />
            <div className="lg:pl-[96px]">
                {/* Show health alerts if not fully healthy */}
                {healthStatus && !healthStatus.healthy && <SystemAlert health={healthStatus} />}

                {/* REV UI23: Show config incomplete warning banner */}
                {configWarnings?.warnings && configWarnings.warnings.length > 0 && (
                    <div className="banner banner-warning px-4 py-3 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span>⚠️</span>
                            <span className="font-medium">
                                Configuration incomplete — {configWarnings.warnings.length} required setting
                                {configWarnings.warnings.length > 1 ? 's' : ''} missing
                            </span>
                            <span className="opacity-70 text-xs">
                                ({configWarnings.warnings.map((w) => w.message).join(', ')})
                            </span>
                        </div>
                        <button
                            onClick={() => setConfigWarnings(null)}
                            className="opacity-60 hover:opacity-100 text-xs px-2 py-1"
                            title="Dismiss"
                        >
                            ✕
                        </button>
                    </div>
                )}

                {/* Show backend offline banner only if no health status available */}
                {backendOffline && !healthStatus && (
                    <div className="bg-amber-900/80 border-b border-amber-500/60 text-amber-100 text-[11px] px-4 py-2 flex items-center justify-between">
                        <span>Backend appears offline or degraded. Some data may be stale or unavailable.</span>
                    </div>
                )}
                <Outlet />
            </div>
        </>
    )
}

// Help React Router find the base path when running under HA Ingress
const getBasename = () => {
    const base = document.querySelector('base')
    const href = base?.getAttribute('href')
    if (href && href.startsWith('/')) {
        return href.replace(/\/$/, '') // Remove trailing slash
    }
    return '/'
}

// Routes Definition
const router = createBrowserRouter(
    createRoutesFromElements(
        <Route path="/" element={<RootLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="executor" element={<Executor />} />
            <Route path="aurora" element={<Aurora />} />
            <Route path="debug" element={<Debug />} />
            <Route path="settings" element={<Settings />} />
            <Route path="design-system" element={<DesignSystem />} />
            <Route path="power-flow-lab" element={<PowerFlowLab />} />
            <Route path="chart-examples" element={<ChartExamples />} />
            {/* Catch all - redirect to dashboard */}
            <Route path="*" element={<Navigate to="/" replace />} />
        </Route>,
    ),
    {
        basename: getBasename(),
        future: {
            v7_relativeSplatPath: true,
            v7_fetcherPersist: true,
            v7_normalizeFormMethod: true,
            v7_partialHydration: true,
            v7_skipActionErrorRevalidation: true,
        },
    },
)

export default function App() {
    return (
        <ErrorBoundary>
            <ToastProvider>
                <RouterProvider router={router} future={{ v7_startTransition: true }} />
            </ToastProvider>
        </ErrorBoundary>
    )
}
