import { createContext } from "react";

export interface User {
  user_id?: string;
  username?: string;
  email?: string;
  roles?: string[];
}

export interface AuthContextType {
  isAuthenticated: boolean;
  setIsAuthenticated: (_value: boolean) => void;
  logout: () => void;
  currentUser?: User | null;
  setCurrentUser?: (_user: User | null) => void;
}

export const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  setIsAuthenticated: (_value: boolean) => {},
  logout: () => {},
  currentUser: null,
  setCurrentUser: (_user: User | null) => {},
});
