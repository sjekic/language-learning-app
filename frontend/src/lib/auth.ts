import { createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut } from 'firebase/auth';
import { auth } from '../firebase';

const AUTH_SERVICE_URL = import.meta.env.VITE_AUTH_SERVICE_URL;
export interface AuthUser {
    id: number;
    firebase_uid: string;
    email: string;
    display_name: string;
    created_at: string;
    updated_at: string;
}

export const signup = async (email: string, password: string, username?: string): Promise<AuthUser> => {
    try {

        console.log("VITE BASE URL from signup", AUTH_SERVICE_URL);
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        const token = await userCredential.user.getIdToken();


        const response = await fetch(`${AUTH_SERVICE_URL}/api/auth/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id_token: token,
                display_name: username
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to sync user with backend');
        }

        const data = await response.json();
        return data.user;
    } catch (error: any) {
        console.error('Signup error:', error);
        throw error;
    }
};

export const login = async (email: string, password: string): Promise<AuthUser> => {
    try {
        console.log("VITE BASE URL from login", AUTH_SERVICE_URL);

        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const token = await userCredential.user.getIdToken();


        const response = await fetch(`${AUTH_SERVICE_URL}/api/auth/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id_token: token
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to verify user with backend');
        }

        const data = await response.json();
        return data.user;
    } catch (error: any) {
        console.error('Login error:', error);
        throw error;
    }
};

export const logout = async (): Promise<void> => {
    await signOut(auth);
};

export const getToken = async (): Promise<string | undefined> => {
    const user = auth.currentUser;
    if (user) {
        return user.getIdToken();
    }
    return undefined;
};

export const getCurrentUser = async (): Promise<AuthUser | null> => {
    const token = await getToken();
    if (!token) return null;

    try {
        const response = await fetch(`${AUTH_SERVICE_URL}/api/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) return null;

        return await response.json();
    } catch (error) {
        console.error('Get current user error:', error);
        return null;
    }
};