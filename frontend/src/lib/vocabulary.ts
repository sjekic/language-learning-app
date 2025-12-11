// Local storage utility for vocabulary management
// This will be replaced with backend API calls later

export interface SavedWord {
    id: string;
    word: string;
    translation: string;
    partOfSpeech: string;
    sourceLanguage: string;
    targetLanguage: string;
    savedAt: string;
    context?: string; // Optional: the sentence/story it came from
}

const STORAGE_KEY = 'saved_vocabulary';

// Get all saved words
export const getSavedWords = (): SavedWord[] => {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (error) {
        console.error('Error reading saved words:', error);
        return [];
    }
};

// Save a new word
export const saveWord = (word: Omit<SavedWord, 'id' | 'savedAt'>): SavedWord => {
    const words = getSavedWords();

    // Check if word already exists (case-insensitive)
    const existing = words.find(
        w => w.word.toLowerCase() === word.word.toLowerCase() &&
            w.sourceLanguage === word.sourceLanguage
    );

    if (existing) {
        return existing; // Don't save duplicates
    }

    const newWord: SavedWord = {
        ...word,
        id: crypto.randomUUID(),
        savedAt: new Date().toISOString(),
    };

    const updatedWords = [...words, newWord];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedWords));

    return newWord;
};

// Delete a saved word
export const deleteSavedWord = (id: string): void => {
    const words = getSavedWords();
    const filtered = words.filter(w => w.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
};

// Check if a word is already saved
export const isWordSaved = (word: string, sourceLanguage: string): boolean => {
    const words = getSavedWords();
    return words.some(
        w => w.word.toLowerCase() === word.toLowerCase() &&
            w.sourceLanguage === sourceLanguage
    );
};

// Get words by language
export const getWordsByLanguage = (sourceLanguage: string): SavedWord[] => {
    const words = getSavedWords();
    return words.filter(w => w.sourceLanguage === sourceLanguage);
};

// Export all words (for future migration to backend)
export const exportWords = (): string => {
    const words = getSavedWords();
    return JSON.stringify(words, null, 2);
};

// Import words (for backup restoration)
export const importWords = (jsonData: string): void => {
    try {
        const words = JSON.parse(jsonData) as SavedWord[];
        localStorage.setItem(STORAGE_KEY, JSON.stringify(words));
    } catch (error) {
        console.error('Error importing words:', error);
        throw new Error('Invalid vocabulary data');
    }
};
