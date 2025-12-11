import React from 'react';
import { Bookmark, BookmarkCheck } from 'lucide-react';
import { saveWord, isWordSaved } from '../lib/vocabulary';

import { translate } from '../lib/translation';

interface StoryPageProps {
    content: string;
    pageNumber: number;
    totalPages: number;
    language: string;
    onWordHover: (word: string) => void;
}

export const StoryPage: React.FC<StoryPageProps> = ({ content, pageNumber, totalPages, language, onWordHover }) => {
    // Split content into words to enable individual hover
    const words = content.split(' ');
    const [hoveredWord, setHoveredWord] = React.useState<{ word: string; index: number } | null>(null);
    const [translation, setTranslation] = React.useState<string | null>(null);
    const [translationDetails, setTranslationDetails] = React.useState<{ text: string; pos: string } | null>(null);
    const [loading, setLoading] = React.useState(false);
    const [savedWords, setSavedWords] = React.useState<Set<string>>(new Set());

    React.useEffect(() => {
        let isMounted = true;

        const fetchTranslation = async () => {
            if (!hoveredWord) {
                setTranslation(null);
                return;
            }

            setLoading(true);
            // Strip punctuation for better translation
            const cleanWord = hoveredWord.word.replace(/[.,!?\"]/g, '');

            try {
                // Default to translating to English for now, can be made dynamic
                const response = await translate(cleanWord, language, 'EN');

                if (isMounted) {
                    if (response.translations && response.translations.length > 0) {
                        // Format: "Translation (Part of Speech)"
                        const firstMatch = response.translations[0];
                        setTranslation(`${firstMatch.text} (${firstMatch.pos})`);
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

    const handleSaveWord = () => {
        if (!hoveredWord || !translationDetails) return;

        const cleanWord = hoveredWord.word.replace(/[.,!?\\"]/g, '');

        saveWord({
            word: cleanWord,
            translation: translationDetails.text,
            partOfSpeech: translationDetails.pos,
            sourceLanguage: language,
            targetLanguage: 'English',
            context: content,
        });

        setSavedWords(prev => new Set(prev).add(cleanWord.toLowerCase()));
    };


    const handleWordClick = (word: string) => {
        const cleanWord = word.replace(/[.,!?\"]/g, '');
        onWordHover(cleanWord);
    };

    return (
        <div className="glass-dark rounded-2xl border border-white/10 p-8 md:p-12 min-h-[500px] flex flex-col relative overflow-hidden backdrop-blur-xl">
            {/* Decorative background element */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-neon-purple/10 rounded-bl-full opacity-50 pointer-events-none" />

            <div className="flex-1">
                <p className="text-lg md:text-xl leading-relaxed text-gray-100 font-serif relative z-10">
                    {words.map((word, index) => (
                        <span
                            key={index}
                            className="inline-block mr-1.5 hover:bg-neon-purple/20 hover:text-neon-purple rounded px-0.5 transition-colors cursor-pointer duration-200 relative"
                            onClick={() => handleWordClick(word)}
                            onMouseEnter={() => setHoveredWord({ word, index })}
                            onMouseLeave={() => setHoveredWord(null)}
                        >
                            {word}
                            {/* Translation Tooltip */}
                            {hoveredWord?.index === index && (
                                <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-dark-800 border border-neon-purple/30 rounded-lg text-sm z-50 shadow-lg backdrop-blur-xl min-w-[200px]">
                                    <div className="flex items-center justify-between gap-3">
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
                                                title={isWordSaved(hoveredWord.word.replace(/[.,!?\\"]/g, ''), language) ? "Already saved" : "Save word"}
                                            >
                                                {isWordSaved(hoveredWord.word.replace(/[.,!?\\"]/g, ''), language) || savedWords.has(hoveredWord.word.replace(/[.,!?\\"]/g, '').toLowerCase()) ? (
                                                    <BookmarkCheck className="w-4 h-4 text-neon-cyan" />
                                                ) : (
                                                    <Bookmark className="w-4 h-4 text-gray-400 hover:text-neon-purple" />
                                                )}
                                            </button>
                                        )}
                                    </div>
                                    <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-dark-800"></span>
                                </span>
                            )}
                        </span>
                    ))}
                </p>
            </div>

            <div className="mt-8 flex justify-center">
                <span className="text-sm font-medium text-gray-400 bg-white/5 border border-white/10 px-4 py-2 rounded-full backdrop-blur">
                    Page {pageNumber} of {totalPages}
                </span>
            </div>
        </div>
    );
};
