import { createContext, useContext } from 'react';
import type { User } from 'firebase/auth';

export const AuthContext = createContext<{ currentUser: User | null }>({ currentUser: null });

export const useAuth = () => useContext(AuthContext);
