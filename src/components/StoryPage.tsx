import React from 'react';
import { cn } from '../lib/utils';

interface StoryPageProps {
    content: string;
    pageNumber: number;
    totalPages: number;
    onWordHover: (word: string) => void;
}

export const StoryPage: React.FC<StoryPageProps> = ({ content, pageNumber, totalPages, onWordHover }) => {
    // Split content into words to enable individual hover
    const words = content.split(' ');

    return (
        <div className="bg-white rounded-2xl shadow-xl shadow-gray-200/50 border border-gray-100 p-8 md:p-12 min-h-[500px] flex flex-col relative overflow-hidden">
            {/* Decorative background element */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary-50 rounded-bl-full opacity-50 pointer-events-none" />

            <div className="flex-1">
                <p className="text-lg md:text-xl leading-relaxed text-gray-800 font-serif">
                    {words.map((word, index) => (
                        <span
                            key={index}
                            className="inline-block mr-1.5 hover:bg-primary-100 hover:text-primary-700 rounded px-0.5 transition-colors cursor-pointer duration-200"
                            onMouseEnter={() => onWordHover(word.replace(/[.,!?"]/g, ''))} // Strip punctuation for cleaner vocab list
                        >
                            {word}
                        </span>
                    ))}
                </p>
            </div>

            <div className="mt-8 flex justify-center">
                <span className="text-sm font-medium text-gray-400 bg-gray-50 px-3 py-1 rounded-full">
                    Page {pageNumber} of {totalPages}
                </span>
            </div>
        </div>
    );
};
