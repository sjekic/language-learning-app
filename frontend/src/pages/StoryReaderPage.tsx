import React, { useState } from 'react';
import { useLocation, useNavigate, useOutletContext } from 'react-router-dom';
import { StoryPage } from '../components/StoryPage';
import { ChevronLeft, ChevronRight, Home } from 'lucide-react';

interface StoryState {
    story: { id: number; content: string }[];
    title: string;
}

interface LayoutContext {
    addHoveredWord: (word: string) => void;
}

export const StoryReaderPage: React.FC = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const { addHoveredWord } = useOutletContext<LayoutContext>();

    const state = location.state as StoryState;
    const [currentPage, setCurrentPage] = useState(0);

    // Redirect if no story data
    React.useEffect(() => {
        if (!state?.story) {
            navigate('/library');
        }
    }, [state, navigate]);

    if (!state?.story) return null;

    const totalPages = state.story.length;
    const currentContent = state.story[currentPage].content;

    const handleNext = () => {
        if (currentPage < totalPages - 1) {
            setCurrentPage(prev => prev + 1);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };

    const handlePrev = () => {
        if (currentPage > 0) {
            setCurrentPage(prev => prev - 1);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };

    return (
        <div className="min-h-screen bg-dark-900 py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto space-y-8">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <button
                        onClick={() => navigate('/library')}
                        className="flex items-center gap-2 px-4 py-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/5"
                    >
                        <Home className="w-4 h-4" />
                        <span className="text-sm">Back to Library</span>
                    </button>
                    <h2 className="font-semibold text-white truncate max-w-[200px] sm:max-w-md text-center">
                        {state.title}
                    </h2>
                    <div className="w-24" /> {/* Spacer for alignment */}
                </div>

                {/* Story Content */}
                <StoryPage
                    content={currentContent}
                    pageNumber={currentPage + 1}
                    totalPages={totalPages}
                    onWordHover={addHoveredWord}
                />

                {/* Navigation */}
                <div className="flex items-center justify-between">
                    <button
                        onClick={handlePrev}
                        disabled={currentPage === 0}
                        className="w-32 px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
                    >
                        <ChevronLeft className="w-4 h-4" />
                        Previous
                    </button>

                    <button
                        onClick={handleNext}
                        disabled={currentPage === totalPages - 1}
                        className="w-32 relative group overflow-hidden rounded-xl bg-gradient-to-r from-neon-purple to-neon-cyan p-[2px] transition-all hover:scale-105 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:scale-100"
                    >
                        <div className="relative bg-dark-900 rounded-[10px] px-4 py-2.5 flex items-center justify-center gap-2 group-hover:bg-transparent transition-all">
                            <span className="font-medium text-white">
                                {currentPage === totalPages - 1 ? 'Finish' : 'Next'}
                            </span>
                            {currentPage !== totalPages - 1 && <ChevronRight className="w-4 h-4" />}
                        </div>
                    </button>
                </div>
            </div>
        </div>
    );
};
