import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

export const Navbar: React.FC = () => {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Link
            to={token ? "/jobs" : "/login"}
            className="flex items-center gap-2 text-xl font-bold tracking-tight text-slate-900"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-semibold text-white shadow-sm">
              VH
            </span>
            <span>VeriHire</span>
          </Link>
          {token && (
            <nav className="hidden sm:flex items-center gap-4 text-sm font-medium">
              <Link
                to="/jobs"
                className="text-slate-600 hover:text-slate-900 transition-colors"
              >
                Jobs
              </Link>
            </nav>
          )}
        </div>

        <div className="flex items-center gap-4">
          {token ? (
            <div className="flex items-center gap-3">
              <span className="hidden sm:inline-block text-xs font-medium text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full border border-slate-200">
                {user?.email || "Authenticated"}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleLogout}
                className="text-xs"
              >
                Log out
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login">
                <Button variant="ghost" size="sm" className="text-xs">
                  Log in
                </Button>
              </Link>
              <Link to="/register">
                <Button size="sm" className="text-xs">
                  Register
                </Button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
