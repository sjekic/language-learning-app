import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { Menu } from 'lucide-react';

export const Layout: React.FC = () => {
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [hoveredWords, setHoveredWords] = useState<string[]>([]);

    const addHoveredWord = (word: string) => {
        if (!hoveredWords.includes(word)) {
            setHoveredWords(prev => [...prev, word]);
        }
    };

    return (
        <div className="flex h-screen overflow-hidden">
            <div className="flex-1 overflow-auto">
                <main className="min-h-screen relative">
                    {/* Mobile Menu Button */}
                    <button
                        onClick={() => setIsSidebarOpen(true)}
                        className="lg:hidden fixed top-4 right-4 z-30 p-3 bg-dark-800/80 backdrop-blur-md border border-white/10 rounded-full text-white shadow-lg hover:bg-dark-700 transition-all"
                    >
                        <Menu className="w-6 h-6" />
                    </button>
                    <Outlet context={{ addHoveredWord }} />
                </main>
            </div>

            {/* Sidebar (only show on story pages or always? User requirement implies it's for Vocab Tracking) */}
            {/* We'll show it always for now, but maybe it's empty on non-story pages. */}
            <Sidebar
                isOpen={isSidebarOpen}
                setIsOpen={setIsSidebarOpen}
                hoveredWords={hoveredWords}
            />
        </div>
    );
};
