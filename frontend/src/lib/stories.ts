import { getToken } from './auth';

const BOOK_SERVICE_URL = import.meta.env.VITE_BOOK_SERVICE_URL || 'http://localhost:8003';

export interface Story {
    id: number;
    title: string;
    content: string;
    difficulty_level: string;
    user_id: number;
    created_at: string;
}

export const getStories = async (): Promise<Story[]> => {
    const token = await getToken();

    console.log("Getting stories with URL: ", BOOK_SERVICE_URL);
    
    const response = await fetch(`${BOOK_SERVICE_URL}/api/stories`, {
        headers: {
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
    });

    if (!response.ok) {
        throw new Error('Failed to fetch stories');
    }

    return await response.json();
};

export const getStory = async (id: number): Promise<Story> => {
    const token = await getToken();

    console.log("Getting story with URL: ", BOOK_SERVICE_URL);
    
    const response = await fetch(`${BOOK_SERVICE_URL}/api/stories/${id}`, {
        headers: {
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
    });

    if (!response.ok) {
        throw new Error('Failed to fetch story');
    }

    return await response.json();
};

export const createStory = async (title: string, content: string, difficulty: string): Promise<Story> => {
    const token = await getToken();
    if (!token) throw new Error('Authentication required');

    console.log("Creating story with URL: ", BOOK_SERVICE_URL);

    const response = await fetch(`${BOOK_SERVICE_URL}/api/stories`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            title,
            content,
            difficulty_level: difficulty
        })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create story');
    }

    return await response.json();
};