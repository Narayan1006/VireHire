import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ProtectedRoute, PublicOnlyRoute } from "@/components/RouteGuards";
import { LoginPage } from "@/pages/Login";
import { RegisterPage } from "@/pages/Register";
import { JobsListPage } from "@/pages/JobsList";
import { JobNewPage } from "@/pages/JobNew";
import { JobDetailPage } from "@/pages/JobDetail";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="flex min-h-screen flex-col bg-white font-sans text-slate-900 antialiased selection:bg-indigo-500 selection:text-white">
          <Navbar />
          <main className="flex-1">
            <Routes>
              {/* Public-only routes (redirect to /jobs if logged in) */}
              <Route
                path="/login"
                element={
                  <PublicOnlyRoute>
                    <LoginPage />
                  </PublicOnlyRoute>
                }
              />
              <Route
                path="/register"
                element={
                  <PublicOnlyRoute>
                    <RegisterPage />
                  </PublicOnlyRoute>
                }
              />

              {/* Protected routes (redirect to /login if unauthenticated) */}
              <Route
                path="/jobs"
                element={
                  <ProtectedRoute>
                    <JobsListPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/jobs/new"
                element={
                  <ProtectedRoute>
                    <JobNewPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/jobs/:id"
                element={
                  <ProtectedRoute>
                    <JobDetailPage />
                  </ProtectedRoute>
                }
              />

              {/* Default redirects */}
              <Route path="/" element={<Navigate to="/jobs" replace />} />
              <Route path="*" element={<Navigate to="/jobs" replace />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}
