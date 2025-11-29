import React from 'react';

interface StoryPageProps {
    content: string;
    pageNumber: number;
    totalPages: number;
    onWordHover: (word: string) => void;
}

export const StoryPage: React.FC<StoryPageProps> = ({ content, pageNumber, totalPages, onWordHover }) => {
    // Split content into words to enable individual hover
    const words = content.split(' ');
    const [hoveredWord, setHoveredWord] = React.useState<{ word: string; index: number } | null>(null);

    // Mock translation function (in real app, this would call an API)
    const getTranslation = (word: string) => {
        // Strip punctuation for better translation
        const cleanWord = word.replace(/[.,!?\"]/g, '');
        // Mock translations (you'd replace this with actual API call)
        return `Translation of "${cleanWord}"`;
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
                                <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-dark-800 border border-neon-purple/30 rounded-lg text-sm text-neon-purple whitespace-nowrap z-50 shadow-lg backdrop-blur-xl">
                                    {getTranslation(word)}
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
