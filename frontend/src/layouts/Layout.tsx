import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';

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
                <main className="min-h-screen">
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
