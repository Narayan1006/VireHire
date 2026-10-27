import React, { createContext, useContext, useEffect, useState } from "react";
import { apiRequest, getStoredToken, setStoredToken } from "@/lib/api";

export interface User {
  id: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, userData?: User) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchCurrentUser = async (): Promise<void> => {
    try {
      const data = await apiRequest<User>("/me");
      setUser(data);
    } catch {
      setUser(null);
      setToken(null);
      setStoredToken(null);
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const savedToken = getStoredToken();
      if (savedToken) {
        setToken(savedToken);
        await fetchCurrentUser();
      } else {
        setUser(null);
        setToken(null);
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = (newToken: string, userData?: User) => {
    setStoredToken(newToken);
    setToken(newToken);
    if (userData) {
      setUser(userData);
    } else {
      fetchCurrentUser();
    }
  };

  const logout = () => {
    setStoredToken(null);
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    await fetchCurrentUser();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
