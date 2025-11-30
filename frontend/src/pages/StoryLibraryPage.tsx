import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Book, Sparkles, Trash2, Filter, X } from 'lucide-react';
import { getStories, deleteStory, type Story } from '../lib/storage';
import { generateStoryCover } from '../lib/generateStoryCover';
import { Select } from '../components/Select';

export const StoryLibraryPage: React.FC = () => {
    const navigate = useNavigate();
    const [stories, setStories] = useState<Story[]>([]);
    const [coverImages, setCoverImages] = useState<Map<string, string>>(new Map());

    // Filter State
    const [selectedLevel, setSelectedLevel] = useState<string>('');
    const [selectedGenre, setSelectedGenre] = useState<string>('');
    const [selectedLanguage, setSelectedLanguage] = useState<string>('');

    useEffect(() => {
        const loadedStories = getStories();
        setStories(loadedStories);

        // Generate cover images
        const newCoverImages = new Map<string, string>();
        loadedStories.forEach(story => {
            const cover = generateStoryCover(
                story.genre as any,
                story.title,
                400,
                600
            );
            newCoverImages.set(story.id, cover);
        });
        setCoverImages(newCoverImages);
    }, []);

    const handleReadStory = (story: Story) => {
        navigate('/read', {
            state: {
                story: story.pages,
                title: story.title,
                language: story.language,
                fromLibrary: true
            }
        });
    };

    const handleDeleteStory = (id: string, e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (confirm('Delete this story?')) {
            deleteStory(id);
            setStories(getStories());
        }
    };

    // Filter Logic
    const filteredStories = stories.filter(story => {
        const matchesLevel = selectedLevel ? story.level === selectedLevel : true;
        const matchesGenre = selectedGenre ? story.genre === selectedGenre : true;
        const matchesLanguage = selectedLanguage ? story.language === selectedLanguage : true;
        return matchesLevel && matchesGenre && matchesLanguage;
    });

    // Get unique options for filters
    const levels = Array.from(new Set(stories.map(s => s.level))).map(l => ({ value: l, label: l }));
    const genres = Array.from(new Set(stories.map(s => s.genre))).map(g => ({ value: g, label: g.charAt(0).toUpperCase() + g.slice(1) }));
    const languages = Array.from(new Set(stories.map(s => s.language))).map(l => ({ value: l, label: l }));

    const clearFilters = () => {
        setSelectedLevel('');
        setSelectedGenre('');
        setSelectedLanguage('');
    };

    const hasActiveFilters = selectedLevel || selectedGenre || selectedLanguage;



    if (stories.length === 0) {
        return (
            <div className="min-h-screen bg-dark-900 flex items-center justify-center p-4">
                <div className="text-center max-w-md">
                    <div className="inline-flex items-center justify-center p-4 bg-neon-purple/10 rounded-full mb-6 backdrop-blur">
                        <Book className="w-12 h-12 text-neon-purple" />
                    </div>
                    <h2 className="text-3xl font-bold text-white mb-3">Your Story Library</h2>
                    <p className="text-gray-400 mb-8">
                        Generate your first immersive language story to get started
                    </p>
                    <div className="flex flex-col gap-3">
                        <button
                            onClick={() => navigate('/generate')}
                            className="relative group overflow-hidden rounded-xl bg-gradient-to-r from-neon-purple to-neon-cyan p-[2px] transition-all hover:scale-105"
                        >
                            <div className="relative bg-dark-900 rounded-[10px] px-6 py-3 flex items-center justify-center gap-2 group-hover:bg-transparent transition-all">
                                <Sparkles className="w-5 h-5 text-white" />
                                <span className="font-semibold text-white">Create Story</span>
                            </div>
                        </button>

                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-dark-900 py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div>
                        <h1 className="text-4xl font-bold text-white mb-2">Your Stories</h1>
                        <p className="text-gray-400">
                            {filteredStories.length} {filteredStories.length === 1 ? 'story' : 'stories'} found
                        </p>
                    </div>



                    {/* Filters */}
                    <div className="flex flex-wrap items-center gap-3">
                        <div className="w-32">
                            <Select
                                value={selectedLanguage}
                                onChange={(e) => setSelectedLanguage(e.target.value)}
                                options={[{ value: '', label: 'Language' }, ...languages]}
                                className="h-10 text-sm"
                            />
                        </div>
                        <div className="w-32">
                            <Select
                                value={selectedLevel}
                                onChange={(e) => setSelectedLevel(e.target.value)}
                                options={[{ value: '', label: 'Level' }, ...levels]}
                                className="h-10 text-sm"
                            />
                        </div>
                        <div className="w-32">
                            <Select
                                value={selectedGenre}
                                onChange={(e) => setSelectedGenre(e.target.value)}
                                options={[{ value: '', label: 'Genre' }, ...genres]}
                                className="h-10 text-sm"
                            />
                        </div>

                        {hasActiveFilters && (
                            <button
                                onClick={clearFilters}
                                className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                                title="Clear Filters"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        )}
                    </div>
                </div>

                {/* Story Grid - Large Cinematic Cards */}
                {filteredStories.length === 0 ? (
                    <div className="text-center py-20">
                        <div className="inline-flex items-center justify-center p-4 bg-white/5 rounded-full mb-4">
                            <Filter className="w-8 h-8 text-gray-500" />
                        </div>
                        <h3 className="text-xl font-semibold text-white mb-2">No stories found</h3>
                        <p className="text-gray-400 mb-6">Try adjusting your filters to see more stories</p>
                        <button
                            onClick={clearFilters}
                            className="text-neon-purple hover:text-white transition-colors font-medium"
                        >
                            Clear all filters
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 md:gap-6">
                        {filteredStories.map((story) => (
                            <div
                                key={story.id}
                                onClick={() => handleReadStory(story)}
                                className="group relative aspect-[2/3] rounded-2xl overflow-hidden cursor-pointer transform transition-all duration-300 hover:scale-105 hover:z-10"
                            >
                                {/* Cover Image */}
                                <img
                                    src={coverImages.get(story.id) || ''}
                                    alt={story.title}
                                    className="absolute inset-0 w-full h-full object-cover"
                                />

                                {/* Gradient Overlay */}
                                <div className="absolute inset-0 story-overlay" />

                                {/* Delete Button - Always Visible */}
                                <div className="absolute top-2 right-2 z-20">
                                    <button
                                        onClick={(e) => handleDeleteStory(story.id, e)}
                                        className="p-2 bg-red-600/90 backdrop-blur rounded-full text-white hover:bg-red-500 transition-all shadow-lg hover:scale-110"
                                        aria-label="Delete story"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>

                                {/* Content */}
                                <div className="absolute inset-0 p-4 flex flex-col justify-end">
                                    <div>
                                        {/* Title */}
                                        <h3 className="text-white font-bold text-lg sm:text-xl mb-3 line-clamp-2 drop-shadow-lg">
                                            {story.title.toUpperCase()}
                                        </h3>

                                        {/* Metadata */}
                                        <div className="flex flex-wrap items-center gap-2 text-xs">
                                            <span className="px-2 py-1 bg-neon-purple/80 backdrop-blur text-white rounded-full font-medium">
                                                {story.level}
                                            </span>
                                            <span className="px-2 py-1 bg-white/20 backdrop-blur text-white rounded-full font-medium">
                                                {story.language}
                                            </span>
                                            <span className="px-2 py-1 bg-black/40 backdrop-blur text-gray-200 rounded-full font-medium border border-white/10">
                                                {story.genre}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {/* Play Icon on Hover */}
                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                                    <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur flex items-center justify-center">
                                        <div className="w-0 h-0 border-l-[20px] border-l-white border-t-[12px] border-t-transparent border-b-[12px] border-b-transparent ml-1" />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
