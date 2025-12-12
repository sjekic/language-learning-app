// LocalStorage utilities for story persistence

export interface Story {
    id: string;
    title: string;
    language: string;
    level: string;
    genre: string;
    pages: { id: number; content: string }[];
    coverUrl?: string;
    createdAt: string;
}

const STORAGE_KEY = 'language-learning-stories';

export const saveStory = (story: Omit<Story, 'id' | 'createdAt'>): Story => {
    const stories = getStories();
    const newStory: Story = {
        ...story,
        id: Date.now().toString(),
        createdAt: new Date().toISOString(),
    };

    stories.unshift(newStory); // Add to beginning
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stories));
    return newStory;
};

export const getStories = (): Story[] => {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (error) {
        console.error('Error loading stories:', error);
        return [];
    }
};

export const getStoryById = (id: string): Story | null => {
    const stories = getStories();
    return stories.find(story => story.id === id) || null;
};

export const deleteStory = (id: string): void => {
    const stories = getStories();
    const filtered = stories.filter(story => story.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
};

export const clearAllStories = (): void => {
    localStorage.removeItem(STORAGE_KEY);
};
