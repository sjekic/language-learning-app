import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { Menu, Sparkles } from 'lucide-react';
import { Button } from '../components/Button';

export const Layout: React.FC = () => {
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [hoveredWords, setHoveredWords] = useState<string[]>([]); // This state should ideally be in a Context
    const location = useLocation();

    // Mock function to add words (will be passed to context later)
    const addHoveredWord = (word: string) => {
        if (!hoveredWords.includes(word)) {
            setHoveredWords((prev) => [...prev, word]);
        }
    };

    // Provide context value (mocking for now, will implement real context if needed)
    // For now, we'll pass props or use a simple context in App.tsx if we want global state.
    // But since Layout wraps everything, we can manage state here for the sidebar.
    // However, the StoryReaderPage needs to update this state.
    // So I should probably create a simple Context.

    return (
        <div className="min-h-screen bg-gray-50 flex">
            <div className="flex-1 flex flex-col min-w-0">
                {/* Header */}
                <header className="bg-white border-b border-gray-200 px-4 sm:px-6 h-16 flex items-center justify-between sticky top-0 z-30">
                    <div className="flex items-center gap-2 text-primary-600">
                        <div className="bg-primary-100 p-2 rounded-lg">
                            <Sparkles className="w-5 h-5" />
                        </div>
                        <h1 className="font-bold text-xl tracking-tight text-gray-900">StoryAI</h1>
                    </div>

                    <div className="flex items-center gap-4">
                        <Button
                            variant="ghost"
                            size="sm"
                            className="lg:hidden"
                            onClick={() => setIsSidebarOpen(true)}
                        >
                            <Menu className="w-5 h-5" />
                        </Button>
                    </div>
                </header>

                {/* Main Content */}
                <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
                    <div className="max-w-4xl mx-auto">
                        {/* We need to pass addHoveredWord to the outlet. 
                 React Router's useOutletContext is perfect for this. */}
                        <Outlet context={{ addHoveredWord }} />
                    </div>
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
