import { getToken } from './auth';

const TRANSLATION_SERVICE_URL = import.meta.env.VITE_TRANSLATION_SERVICE_URL || 'http://localhost:8004';

// Map language names to ISO 639-1 codes
const LANGUAGE_CODE_MAP: Record<string, string> = {
    'Spanish': 'es',
    'French': 'fr',
    'German': 'de',
    'Italian': 'it',
    'Portuguese': 'pt',
    'English': 'en',
    'Chinese': 'zh',
    'Japanese': 'ja',
    'Korean': 'ko',
    'Arabic': 'ar',
    'Russian': 'ru',
};

// Convert language name to code (case-insensitive)
const getLanguageCode = (language: string): string => {
    // If already a 2-letter code, return as-is
    if (language.length === 2) return language.toLowerCase();
    
    // Look up in map
    const code = LANGUAGE_CODE_MAP[language] || LANGUAGE_CODE_MAP[language.toLowerCase()];
    return code || language.toLowerCase(); // Fallback to lowercase input
};

export interface TranslationRequest {
    text: string;
    source_lang: string;
    target_lang: string;
}

export interface TranslationResponse {
    word: string;
    translations: string[];
    source_lang: string;
    target_lang: string;
    examples?: Array<{
        src: string;
        dst: string;
    }>;
}

export const translate = async (text: string, sourceLang: string = 'es', targetLang: string = 'en'): Promise<TranslationResponse> => {
    const token = await getToken();

    // Convert language names to codes
    const srcCode = getLanguageCode(sourceLang);
    const dstCode = getLanguageCode(targetLang);

    console.log(`Translating "${text}" from ${sourceLang}(${srcCode}) to ${targetLang}(${dstCode})`);
    console.log('Auth token:', token ? `${token.substring(0, 20)}...` : 'NO TOKEN');
    
    // Check if user is authenticated
    if (!token) {
        throw new Error('Not authenticated. Please log in to use translations.');
    }
    
    // Build query params
    const params = new URLSearchParams({
        query: text,
        src: srcCode,
        dst: dstCode
    });
    
    const response = await fetch(`${TRANSLATION_SERVICE_URL}/api/translate?${params}`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });

    if (!response.ok) {
        let errorMessage = 'Translation failed';
        try {
            const error = await response.json();
            errorMessage = error.detail || errorMessage;
        } catch {
            // If can't parse JSON, use status text
            errorMessage = response.statusText || `HTTP ${response.status}`;
        }
        throw new Error(errorMessage);
    }

    return await response.json();
};