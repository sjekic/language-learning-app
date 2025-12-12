import { getToken } from './auth';

/**
 * Vocabulary storage:
 * - Primary: translation-service `/api/vocabulary` (per-user, persisted in Postgres)
 * - Fallback: localStorage (when not authenticated or backend unavailable)
 */

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

type SavedWordInput = Omit<SavedWord, 'id' | 'savedAt'>;

type ApiVocabularyWord = {
    id: number;
    word: string;
    translation: string;
    language_code: string;
    book_id: number;
    hover_count: number;
    last_seen_at?: string | null;
    created_at: string;
};

const TRANSLATION_SERVICE_URL = import.meta.env.VITE_TRANSLATION_SERVICE_URL || 'http://localhost:8004';

const STORAGE_KEY = 'saved_vocabulary';

export const toLanguageCode = (language: string): string => {
    const l = language.trim().toLowerCase();
    if (l.length === 2) return l;

    const mapping: Record<string, string> = {
        spanish: 'es',
        french: 'fr',
        german: 'de',
        italian: 'it',
        portuguese: 'pt',
        russian: 'ru',
        japanese: 'ja',
        chinese: 'zh',
        english: 'en',
    };

    return mapping[l] || l.slice(0, 2);
};

const apiToSavedWord = (v: ApiVocabularyWord): SavedWord => ({
    id: String(v.id),
    word: v.word,
    translation: v.translation,
    partOfSpeech: 'N/A',
    sourceLanguage: v.language_code,
    targetLanguage: 'English',
    savedAt: v.created_at,
});

const getSavedWordsLocal = (): SavedWord[] => {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (error) {
        console.error('Error reading saved words:', error);
        return [];
    }
};

const saveWordLocal = (word: SavedWordInput): SavedWord => {
    const words = getSavedWordsLocal();

    const existing = words.find(
        (w) => w.word.toLowerCase() === word.word.toLowerCase() && w.sourceLanguage === word.sourceLanguage
    );
    if (existing) return existing;

    const newWord: SavedWord = {
        ...word,
        id: crypto.randomUUID(),
        savedAt: new Date().toISOString(),
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify([...words, newWord]));
    return newWord;
};

const deleteSavedWordLocal = (id: string): void => {
    const words = getSavedWordsLocal();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(words.filter((w) => w.id !== id)));
};

export const getSavedWords = async (): Promise<SavedWord[]> => {
    const token = await getToken();
    if (!token) return getSavedWordsLocal();

    try {
        const response = await fetch(`${TRANSLATION_SERVICE_URL}/api/vocabulary`, {
            headers: { Authorization: `Bearer ${token}` },
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch vocabulary (HTTP ${response.status})`);
        }

        const data = (await response.json()) as ApiVocabularyWord[];
        return data.map(apiToSavedWord);
    } catch (error) {
        console.warn('Falling back to local vocabulary storage:', error);
        return getSavedWordsLocal();
    }
};

export const saveWord = async (word: SavedWordInput): Promise<SavedWord> => {
    console.log("a;osdihf apsodihf ads")
    const token = await getToken();
    if (!token) return saveWordLocal(word);

    try {
        const response = await fetch(`${TRANSLATION_SERVICE_URL}/api/vocabulary`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
                word: word.word,
                translation: word.translation,
                language_code: toLanguageCode(word.sourceLanguage),
                // book_id intentionally omitted; backend will attach to a per-user "Vocabulary" book
            }),
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Failed to save word (HTTP ${response.status})`);
        }

        const saved = (await response.json()) as ApiVocabularyWord;
        return apiToSavedWord(saved);
    } catch (error) {
        console.warn('Falling back to local saveWord:', error);
        return saveWordLocal(word);
    }
};

export const deleteSavedWord = async (id: string): Promise<void> => {
    const token = await getToken();
    if (!token) return deleteSavedWordLocal(id);

    try {
        const response = await fetch(`${TRANSLATION_SERVICE_URL}/api/vocabulary/${id}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${token}` },
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Failed to delete word (HTTP ${response.status})`);
        }
    } catch (error) {
        console.warn('Falling back to local deleteSavedWord:', error);
        deleteSavedWordLocal(id);
    }
};

export const exportWords = async (): Promise<string> => {
    const words = await getSavedWords();
    return JSON.stringify(words, null, 2);
};

export const importWords = (jsonData: string): void => {
    try {
        const words = JSON.parse(jsonData) as SavedWord[];
        localStorage.setItem(STORAGE_KEY, JSON.stringify(words));
    } catch (error) {
        console.error('Error importing words:', error);
        throw new Error('Invalid vocabulary data');
    }
};
