import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Landing } from './pages/Landing'
import { Dashboard } from './pages/Dashboard'
import { CandidateDetail } from './pages/CandidateDetail'
import { CandidateSubmit } from './pages/CandidateSubmit'
import { Login } from './pages/Login'
import { Signup } from './pages/Signup'
import { GrainOverlay } from './components/shared/GrainOverlay'
import { CustomCursor } from './components/shared/CustomCursor'
import { ProtectedRoute } from './components/shared/ProtectedRoute'
import { AuthProvider } from './context/AuthContext'

const fade = { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } }
const transition = { duration: 0.3 }

function AnimatedRoutes() {
  const location = useLocation()

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>

        {/* Public */}
        <Route
          path="/"
          element={<motion.div {...fade} transition={transition}><Landing /></motion.div>}
        />
        <Route
          path="/login"
          element={<motion.div {...fade} transition={transition}><Login /></motion.div>}
        />
        <Route
          path="/signup"
          element={<motion.div {...fade} transition={transition}><Signup /></motion.div>}
        />

        {/* Protected */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <motion.div {...fade} transition={transition}><Dashboard /></motion.div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/candidate"
          element={
            <ProtectedRoute>
              <motion.div {...fade} transition={transition}><CandidateSubmit /></motion.div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/candidate/:id"
          element={
            <ProtectedRoute>
              <motion.div {...fade} transition={transition}><CandidateDetail /></motion.div>
            </ProtectedRoute>
          }
        />

      </Routes>
    </AnimatePresence>
  )
}

export function App() {
  return (
    <AuthProvider>
      <GrainOverlay />
      <CustomCursor />
      <AnimatedRoutes />
    </AuthProvider>
  )
}
