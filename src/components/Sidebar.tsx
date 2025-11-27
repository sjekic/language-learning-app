import React from 'react';
import { cn } from '../lib/utils';
import { BookOpen, ChevronLeft, ChevronRight } from 'lucide-react';
import { WordPill } from './WordPill';

interface SidebarProps {
    isOpen: boolean;
    setIsOpen: (isOpen: boolean) => void;
    hoveredWords: string[];
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, setIsOpen, hoveredWords }) => {
    return (
        <>
            {/* Mobile Overlay */}
            <div
                className={cn(
                    'fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-300',
                    isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
                )}
                onClick={() => setIsOpen(false)}
            />

            {/* Sidebar */}
            <aside
                className={cn(
                    'fixed top-0 right-0 h-full w-80 bg-white border-l border-gray-200 shadow-2xl z-50 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:shadow-none lg:z-0',
                    isOpen ? 'translate-x-0' : 'translate-x-full'
                )}
            >
                <div className="flex flex-col h-full">
                    <div className="p-6 border-b border-gray-100 flex items-center justify-between">
                        <div className="flex items-center gap-2 text-primary-600">
                            <BookOpen className="w-5 h-5" />
                            <h2 className="font-semibold text-lg">Vocabulary</h2>
                        </div>
                        <button
                            onClick={() => setIsOpen(false)}
                            className="lg:hidden p-2 text-gray-400 hover:text-gray-600"
                        >
                            <ChevronRight className="w-5 h-5" />
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto p-6">
                        {hoveredWords.length === 0 ? (
                            <div className="text-center text-gray-400 mt-10">
                                <p className="text-sm">Hover over words in the story to collect them here.</p>
                            </div>
                        ) : (
                            <div className="flex flex-wrap gap-2">
                                {hoveredWords.map((word, index) => (
                                    <WordPill key={`${word}-${index}`} word={word} />
                                ))}
                            </div>
                        )}

                        <div className="mt-8 p-4 bg-gray-50 rounded-xl border border-gray-100 text-center">
                            <p className="text-xs text-gray-500 font-medium">Translations coming soon!</p>
                        </div>
                    </div>
                </div>
            </aside>
        </>
    );
};
