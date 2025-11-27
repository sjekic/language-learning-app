import React, { useState } from 'react';
import { useLocation, useNavigate, useOutletContext } from 'react-router-dom';
import { Button } from '../components/Button';
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
            navigate('/generate');
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
        <div className="max-w-3xl mx-auto py-8 space-y-8">
            <div className="flex items-center justify-between">
                <Button variant="ghost" size="sm" onClick={() => navigate('/generate')}>
                    <Home className="w-4 h-4 mr-2" />
                    Back to Generator
                </Button>
                <h2 className="font-semibold text-gray-900 truncate max-w-[200px] sm:max-w-md">
                    {state.title}
                </h2>
                <div className="w-24" /> {/* Spacer for alignment */}
            </div>

            <StoryPage
                content={currentContent}
                pageNumber={currentPage + 1}
                totalPages={totalPages}
                onWordHover={addHoveredWord}
            />

            <div className="flex items-center justify-between">
                <Button
                    variant="secondary"
                    onClick={handlePrev}
                    disabled={currentPage === 0}
                    className="w-32"
                >
                    <ChevronLeft className="w-4 h-4 mr-2" />
                    Previous
                </Button>

                <Button
                    variant="primary"
                    onClick={handleNext}
                    disabled={currentPage === totalPages - 1}
                    className="w-32"
                >
                    {currentPage === totalPages - 1 ? 'Finish' : 'Next'}
                    {currentPage !== totalPages - 1 && <ChevronRight className="w-4 h-4 ml-2" />}
                </Button>
            </div>
        </div>
    );
};
