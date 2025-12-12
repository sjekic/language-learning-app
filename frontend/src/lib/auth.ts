import { createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut, updateProfile } from 'firebase/auth';
import { auth } from '../firebase';

export interface AuthUser {
    uid: string;
    email: string;
    displayName: string;
}

export const signup = async (email: string, password: string, username?: string): Promise<AuthUser> => {
    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        
        // Update display name if provided
        if (username) {
            await updateProfile(userCredential.user, { displayName: username });
        }
        
        return {
            uid: userCredential.user.uid,
            email: userCredential.user.email || email,
            displayName: username || userCredential.user.email?.split('@')[0] || 'User'
        };
    } catch (error: any) {
        console.error('Signup error:', error);
        throw error;
    }
};

export const login = async (email: string, password: string): Promise<AuthUser> => {
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        
        return {
            uid: userCredential.user.uid,
            email: userCredential.user.email || email,
            displayName: userCredential.user.displayName || userCredential.user.email?.split('@')[0] || 'User'
        };
    } catch (error: any) {
        console.error('Login error:', error);
        throw error;
    }
};

export const logout = async (): Promise<void> => {
    await signOut(auth);
};

export const getToken = async (): Promise<string | undefined> => {
    // Wait for Firebase to initialize if needed
    return new Promise((resolve) => {
        const unsubscribe = auth.onAuthStateChanged((user) => {
            unsubscribe(); // Stop listening after first check
            if (user) {
                user.getIdToken().then(resolve).catch(() => resolve(undefined));
            } else {
                resolve(undefined);
            }
        });
    });
};

export const getCurrentUser = async (): Promise<AuthUser | null> => {
    return new Promise((resolve) => {
        const unsubscribe = auth.onAuthStateChanged((user) => {
            unsubscribe();
            if (user) {
                resolve({
                    uid: user.uid,
                    email: user.email || '',
                    displayName: user.displayName || user.email?.split('@')[0] || 'User'
                });
            } else {
                resolve(null);
            }
        });
    });
};