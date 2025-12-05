import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { cn } from '../lib/utils';
import { BookOpen, ChevronRight, Sparkles, Library, BookMarked } from 'lucide-react';
import { WordPill } from './WordPill';

interface SidebarProps {
    isOpen: boolean;
    setIsOpen: (isOpen: boolean) => void;
    hoveredWords: string[];
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, setIsOpen, hoveredWords }) => {
    const navigate = useNavigate();
    const location = useLocation();

    const menuItems = [
        { icon: Library, label: 'Library', path: '/library' },
        { icon: Sparkles, label: 'Create Story', path: '/generate' },
        { icon: BookMarked, label: 'Vocabulary', path: '/vocabulary' },
    ];

    return (
        <>
            {/* Mobile Overlay */}
            <div
                className={cn(
                    'fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-300',
                    isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
                )}
                onClick={() => setIsOpen(false)}
            />

            {/* Sidebar */}
            <aside
                className={cn(
                    'fixed top-0 right-0 h-full w-80 bg-dark-800 border-l border-white/10 shadow-2xl z-50 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:shadow-none lg:z-0',
                    isOpen ? 'translate-x-0' : 'translate-x-full'
                )}
            >
                <div className="flex flex-col h-full">
                    {/* Header */}
                    <div className="p-6 border-b border-white/10 flex items-center justify-between">
                        <div className="flex items-center gap-2 text-neon-purple">
                            <BookOpen className="w-6 h-6" />
                            <h2 className="font-bold text-xl text-white tracking-tight">StoryAI</h2>
                        </div>
                        <button
                            onClick={() => setIsOpen(false)}
                            className="lg:hidden p-2 text-gray-400 hover:text-white transition-colors"
                        >
                            <ChevronRight className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Navigation */}
                    <div className="p-4 space-y-2">
                        {menuItems.map((item) => {
                            const Icon = item.icon;
                            const isActive = location.pathname === item.path;
                            return (
                                <button
                                    key={item.path}
                                    onClick={() => {
                                        navigate(item.path);
                                        setIsOpen(false);
                                    }}
                                    className={cn(
                                        'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group',
                                        isActive
                                            ? 'bg-neon-purple/10 text-white shadow-[0_0_20px_rgba(139,92,246,0.1)] border border-neon-purple/20'
                                            : 'text-gray-400 hover:bg-white/5 hover:text-white'
                                    )}
                                >
                                    <Icon className={cn("w-5 h-5 transition-colors", isActive ? "text-neon-purple" : "group-hover:text-neon-purple")} />
                                    <span className="font-medium">{item.label}</span>
                                    {isActive && (
                                        <div className="ml-auto w-1.5 h-1.5 rounded-full bg-neon-purple shadow-[0_0_10px_#8b5cf6]" />
                                    )}
                                </button>
                            );
                        })}
                    </div>

                    {/* Vocabulary Section - Only show if there are words or on read page */}
                    <div className="flex-1 overflow-y-auto p-6 border-t border-white/10">
                        <div className="flex items-center gap-2 mb-4 text-gray-400">
                            <BookOpen className="w-4 h-4" />
                            <h3 className="text-xs font-bold uppercase tracking-wider">Vocabulary</h3>
                        </div>

                        {hoveredWords.length === 0 ? (
                            <div className="text-center text-gray-500 py-8 bg-white/5 rounded-xl border border-white/5 border-dashed">
                                <p className="text-sm">Click words while reading to collect them here.</p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="flex flex-wrap gap-2">
                                    {hoveredWords.map((word, index) => (
                                        <WordPill key={`${word}-${index}`} word={word} />
                                    ))}
                                </div>
                                <div className="p-3 bg-dark-700 rounded-lg border border-white/10 text-center backdrop-blur">
                                    <p className="text-xs text-gray-400 font-medium">Translations coming soon! ✨</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </aside>
        </>
    );
};
