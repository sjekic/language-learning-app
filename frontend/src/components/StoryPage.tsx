import React from 'react';
import { Bookmark, BookmarkCheck } from 'lucide-react';
import { saveWord, getSavedWords, toLanguageCode } from '../lib/vocabulary';

import { translate } from '../lib/translation';
import type { TranslationResponse } from '../lib/translation';

interface StoryPageProps {
    content: string;
    pageNumber: number;
    totalPages: number;
    language: string;
    onWordHover: (word: string) => void;
}

export const StoryPage: React.FC<StoryPageProps> = ({ content, pageNumber, totalPages, language, onWordHover }) => {
    // Parse content into paragraphs and handle markdown
    const parseContent = (text: string) => {
        // Split by double newlines for paragraphs, or periods followed by capital letters
        const paragraphs = text
            .split(/\n\n+/)
            .map(p => p.trim())
            .filter(p => p.length > 0);
        
        return paragraphs.map(paragraph => {
            // Check if it's a title (surrounded by **)
            const titleMatch = paragraph.match(/^\*\*(.+?)\*\*$/);
            if (titleMatch) {
                return { type: 'title' as const, text: titleMatch[1] };
            }
            return { type: 'paragraph' as const, text: paragraph.replace(/\*\*/g, '') };
        });
    };

    const parsedContent = parseContent(content);
    const [hoveredWord, setHoveredWord] = React.useState<{ word: string; index: number } | null>(null);
    const [translation, setTranslation] = React.useState<string | null>(null);
    const [translationDetails, setTranslationDetails] = React.useState<TranslationResponse | null>(null);
    const [loading, setLoading] = React.useState(false);
    const [savedWords, setSavedWords] = React.useState<Set<string>>(new Set());

    // Prefetch saved vocabulary words so the UI can show "saved" state without blocking renders.
    React.useEffect(() => {
        let mounted = true;
        (async () => {
            try {
                const all = await getSavedWords();
                const langCode = toLanguageCode(language);
                const set = new Set(
                    all
                        .filter(w => toLanguageCode(w.sourceLanguage) === langCode)
                        .map(w => w.word.toLowerCase())
                );
                if (mounted) setSavedWords(set);
            } catch {
                // ignore (backend might be down; local fallback handled in lib)
            }
        })();
        return () => {
            mounted = false;
        };
    }, [language]);

    React.useEffect(() => {
        let isMounted = true;

        const fetchTranslation = async () => {
            if (!hoveredWord) {
                setTranslation(null);
                return;
            }

            setLoading(true);
            // Strip punctuation for better translation
            const cleanWord = hoveredWord.word.replace(/[.,!?"]/g, '');

            try {
                // Default to translating to English for now, can be made dynamic
                const response = await translate(cleanWord, language, 'en');

                if (isMounted) {
                    if (response.translations && response.translations.length > 0) {
                        // Backend returns array of strings
                        const firstTranslation = response.translations[0];
                        setTranslation(firstTranslation);
                        setTranslationDetails(response);
                    } else {
                        setTranslation('No translation found');
                        setTranslationDetails(null);
                    }
                }
            } catch (error) {
                console.error('Translation error:', error);
                if (isMounted) setTranslation('Error translating');
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        // Debounce translation requests
        const timeoutId = setTimeout(fetchTranslation, 300);

        return () => {
            isMounted = false;
            clearTimeout(timeoutId);
        };
    }, [hoveredWord, language]);

    const handleSaveWord = async () => {
        if (!hoveredWord || !translationDetails) return;

        const cleanWord = hoveredWord.word.replace(/[.,!?"]/g, '');

        try {
            await saveWord({
                word: cleanWord,
                translation: translationDetails.translations[0] || 'N/A',
                partOfSpeech: 'N/A', // Backend doesn't provide part of speech
                sourceLanguage: language,
                targetLanguage: 'English',
                context: content,
            });
            setSavedWords(prev => new Set(prev).add(cleanWord.toLowerCase()));
        } catch (e) {
            console.error('Failed to save word:', e);
        }
    };


    const handleWordClick = (word: string) => {
        const cleanWord = word.replace(/[.,!?"]/g, '');
        onWordHover(cleanWord);

        // Clicking a word should "collect" it into the user's vocabulary.
        // Prefer using the currently loaded translationDetails if it matches; otherwise fetch on demand.
        const key = cleanWord.toLowerCase();
        if (savedWords.has(key)) return;

        let translationText: string = 'N/A';
        try {
            const matchesCurrent =
                translationDetails &&
                translationDetails.word &&
                translationDetails.word.toLowerCase() === cleanWord.toLowerCase() &&
                translationDetails.translations?.length > 0;

            if (matchesCurrent) {
                translationText = translationDetails.translations[0] || 'N/A';
            } else {
                const response = await translate(cleanWord, language, 'en');
                translationText = response.translations?.[0] || 'N/A';
            }
        } catch {
            // If translation fails (e.g. not authenticated), still save the word with a placeholder translation.
        }

        try {
            await saveWord({
                word: cleanWord,
                translation: translationText,
                partOfSpeech: 'N/A',
                sourceLanguage: language,
                targetLanguage: 'English',
                context: content,
            });
            setSavedWords(prev => new Set(prev).add(key));
        } catch (e) {
            console.error('Failed to save word on click:', e);
        }
    };

    return (
        <div className="glass-dark rounded-2xl border border-white/10 p-8 md:p-12 min-h-[500px] flex flex-col relative overflow-hidden backdrop-blur-xl">
            {/* Decorative background element */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-neon-purple/10 rounded-bl-full opacity-50 pointer-events-none" />

            <div className="flex-1 space-y-6">
                {parsedContent.map((block, blockIdx) => {
                    const blockWords = block.text.split(' ');
                    const wordOffset = parsedContent.slice(0, blockIdx).reduce((acc, b) => acc + b.text.split(' ').length, 0);

                    if (block.type === 'title') {
                        return (
                            <h2 key={blockIdx} className="text-2xl md:text-3xl font-bold text-neon-cyan mb-4 relative z-10">
                                {block.text}
                            </h2>
                        );
                    }

                    return (
                        <p key={blockIdx} className="text-lg md:text-xl leading-relaxed text-gray-100 font-serif relative z-10">
                            {blockWords.map((word, wordIdx) => {
                                const globalIndex = wordOffset + wordIdx;
                                return (
                                    <span
                                        key={`${blockIdx}-${wordIdx}`}
                                        className="inline-block mr-1.5 hover:bg-neon-purple/20 hover:text-neon-purple rounded px-0.5 transition-colors cursor-pointer duration-200 relative"
                                        onClick={() => handleWordClick(word)}
                                        onMouseEnter={() => setHoveredWord({ word, index: globalIndex })}
                                        onMouseLeave={() => setHoveredWord(null)}
                                    >
                                        {word}
                                        {/* Translation Tooltip */}
                                        {hoveredWord?.index === globalIndex && (
                                            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-dark-800 border border-neon-purple/30 rounded-lg text-sm z-50 shadow-lg backdrop-blur-xl min-w-[200px]">
                                                <span className="flex items-center justify-between gap-3">
                                                    <span className="text-neon-purple">
                                                        {loading ? 'Translating...' : translation}
                                                    </span>
                                                    {!loading && translationDetails && (
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleSaveWord();
                                                            }}
                                                            className="p-1 hover:bg-neon-purple/20 rounded transition-colors"
                                                                title={isWordSaved(hoveredWord.word.replace(/[.,!?"]/g, ''), language) ? "Already saved" : "Save word"}
                                                            >
                                                                {isWordSaved(hoveredWord.word.replace(/[.,!?"]/g, ''), language) || savedWords.has(hoveredWord.word.replace(/[.,!?"]/g, '').toLowerCase()) ? (
                                                                <BookmarkCheck className="w-4 h-4 text-neon-cyan" />
                                                            ) : (
                                                                <Bookmark className="w-4 h-4 text-gray-400 hover:text-neon-purple" />
                                                            )}
                                                        </button>
                                                    )}
                                                </span>
                                                <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-dark-800"></span>
                                            </span>
                                        )}
                                    </span>
                                );
                            })}
                        </p>
                    );
                })}
            </div>

            <div className="mt-8 flex justify-center">
                <span className="text-sm font-medium text-gray-400 bg-white/5 border border-white/10 px-4 py-2 rounded-full backdrop-blur">
                    Page {pageNumber} of {totalPages}
                </span>
            </div>
        </div>
    );
};
