import axios from 'axios';

const API_URL = 'http://localhost:3001/api/translate';

// Map full language names to ISO 639-1 codes
const LANGUAGE_CODES: { [key: string]: string } = {
    'English': 'en',
    'Spanish': 'es',
    'French': 'fr',
    'German': 'de',
    'Italian': 'it',
    'Portuguese': 'pt',
    'Russian': 'ru',
    'Chinese': 'zh',
    'Japanese': 'ja',
    'Korean': 'ko',
    'Dutch': 'nl',
    'Polish': 'pl',
    'Swedish': 'sv',
    'Danish': 'da',
    'Finnish': 'fi',
    'Greek': 'el',
    'Czech': 'cs',
    'Romanian': 'ro',
    'Hungarian': 'hu',
    'Slovak': 'sk',
    'Bulgarian': 'bg',
    'Slovenian': 'sl',
    'Lithuanian': 'lt',
    'Latvian': 'lv',
    'Estonian': 'et',
    'Maltese': 'mt'
};

export interface TranslationResult {
    text: string;
    pos: string; // Part of speech
}

// Client-side cache
const clientCache = new Map<string, TranslationResult[]>();

export const translateWord = async (word: string, sourceLang: string, targetLang: string = 'English'): Promise<TranslationResult[]> => {
    try {
        const src = LANGUAGE_CODES[sourceLang] || sourceLang.toLowerCase().slice(0, 2);
        const dst = LANGUAGE_CODES[targetLang] || targetLang.toLowerCase().slice(0, 2);

        const cacheKey = `${src}:${dst}:${word.toLowerCase()}`;

        // Check client cache
        if (clientCache.has(cacheKey)) {
            return clientCache.get(cacheKey)!;
        }

        const response = await axios.get(API_URL, {
            params: {
                query: word,
                src,
                dst
            }
        });

        // Parse Linguee API response
        // The API returns a list of matches. We want the translations.
        if (response.data && response.data.length > 0) {
            const firstMatch = response.data[0];
            if (firstMatch.translations) {
                const results = firstMatch.translations.map((t: any) => ({
                    text: t.text,
                    pos: t.pos || firstMatch.pos || 'unknown'
                }));

                // Store in cache
                clientCache.set(cacheKey, results);
                return results;
            }
        }

        return [];
    } catch (error) {
        console.error('Translation error:', error);
        return [];
    }
};
