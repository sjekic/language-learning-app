import { getToken } from './auth';

const USER_SERVICE_URL = import.meta.env.VITE_USER_SERVICE_URL || 'http://localhost:8002';

export interface UserProfile {
    id: number;
    firebase_uid: string;
    email: string;
    display_name: string;
    native_language?: string;
    target_language?: string;
}

export const getUserProfile = async (): Promise<UserProfile> => {
    const token = await getToken();
    if (!token) throw new Error('Authentication required');

    const response = await fetch(`${USER_SERVICE_URL}/api/users/me`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });

    if (!response.ok) {
        throw new Error('Failed to fetch user profile');
    }

    return await response.json();
};

export const updateUserProfile = async (data: Partial<UserProfile>): Promise<UserProfile> => {
    const token = await getToken();
    if (!token) throw new Error('Authentication required');

    const response = await fetch(`${USER_SERVICE_URL}/api/users/me`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(data)
    });

    if (!response.ok) {
        throw new Error('Failed to update user profile');
    }

    return await response.json();
};