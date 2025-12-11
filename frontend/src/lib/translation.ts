import { getToken } from './auth';

const TRANSLATION_SERVICE_URL = import.meta.env.VITE_TRANSLATION_SERVICE_URL || 'http://localhost:8004';

export interface TranslationRequest {
    text: string;
    source_lang: string;
    target_lang: string;
}

export interface TranslationResponse {
    translations: Array<{ 
        text: string; 
        pos: string; 
    }>;
}

export const translate = async (text: string, sourceLang: string = 'EN', targetLang: string = 'DE'): Promise<TranslationResponse> => {
    const token = await getToken();
    
    const response = await fetch(`${TRANSLATION_SERVICE_URL}/api/translate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
            text,
            source_lang: sourceLang,
            target_lang: targetLang
        })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Translation failed');
    }

    return await response.json();
};