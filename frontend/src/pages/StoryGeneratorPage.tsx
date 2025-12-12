import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Select } from '../components/Select';
import { Sparkles } from 'lucide-react';
import { saveStory } from '../lib/storage';
import { generateStory, pollStoryCompletion } from '../lib/storyApi';

export const StoryGeneratorPage: React.FC = () => {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [currentPage, setCurrentPage] = useState(0);
    const [formData, setFormData] = useState({
        level: 'B1',
        genre: 'fantasy',
        language: 'Spanish',
        prompt: '',
    });

    const TOTAL_PAGES = 10;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setProgress(0);
        setCurrentPage(0);

        try {
            // Step 1: Start story generation
            const { story_id } = await generateStory({
                language: formData.language,
                level: formData.level,
                genre: formData.genre,
                prompt: formData.prompt,
            });

            console.log('Story generation started:', story_id);

            // Step 2: Poll for completion with progress updates
            const result = await pollStoryCompletion(
                story_id,
                (status) => {
                    // Update progress based on chunks completed
                    if (status.chunks_completed !== undefined) {
                        const progress = (status.chunks_completed / TOTAL_PAGES) * 100;
                        setProgress(progress);
                        setCurrentPage(status.chunks_completed);
                    }
                },
                2000, // Poll every 2 seconds
                150   // Max 5 minutes (150 * 2s = 300s)
            );

            // Step 3: Process the completed story
            if (result.status === 'completed' && result.story) {
                const pages = result.story.content.map((content, index) => ({
                    id: index + 1,
                    content,
                }));

                // Save to localStorage
                saveStory({
                    title: result.story.title || formData.prompt || `My ${formData.language} Story`,
                    language: formData.language,
                    level: formData.level,
                    genre: formData.genre,
                    pages,
                });

                // Navigate to story reader
                setIsLoading(false);
                navigate('/read', {
                    state: {
                        story: pages,
                        title: result.story.title || formData.prompt || `My ${formData.language} Story`,
                    },
                });
            } else {
                throw new Error('Story generation did not complete successfully');
            }
        } catch (error) {
            console.error('Story generation failed:', error);
            alert('Failed to generate story. Please try again.');
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-dark-900 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl mx-auto">
                <div className="text-center mb-10">
                    <div className="inline-flex items-center justify-center p-4 bg-neon-purple/10 rounded-full mb-6 backdrop-blur">
                        <Sparkles className="w-10 h-10 text-neon-purple" />
                    </div>
                    <h1 className="text-4xl font-bold text-white mb-3">Create Your AI Story</h1>
                    <p className="text-gray-400 text-lg">
                        Generate a personalized 10-page story tailored to your language level
                    </p>
                </div>

                <div className="glass-dark rounded-2xl border border-white/10 p-8 backdrop-blur-xl">
                    {isLoading ? (
                        <div className="flex flex-col items-center justify-center py-16 space-y-8">
                            <div className="relative">
                                <div className="w-24 h-24 border-4 border-white/10 border-t-neon-purple rounded-full animate-spin"></div>
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <Sparkles className="w-10 h-10 text-neon-purple animate-pulse" />
                                </div>
                            </div>

                            <div className="w-full max-w-md space-y-4">
                                <div className="text-center space-y-2">
                                    <p className="text-2xl font-bold text-white">
                                        Generating Your Story
                                    </p>
                                    <p className="text-sm text-gray-400">
                                        Page {currentPage} of {TOTAL_PAGES}
                                    </p>
                                </div>

                                {/* Progress Bar */}
                                <div className="relative">
                                    {/* Background Track */}
                                    <div className="h-3 bg-white/5 rounded-full overflow-hidden border border-white/10">
                                        {/* Animated Progress Fill */}
                                        <div
                                            className="h-full bg-gradient-to-r from-neon-purple via-neon-cyan to-neon-purple bg-[length:200%_100%] animate-gradient-shift relative transition-all duration-300 ease-out"
                                            style={{ width: `${progress}%` }}
                                        >
                                            {/* Glowing effect */}
                                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer"></div>
                                        </div>
                                    </div>

                                    {/* Percentage Label */}
                                    <div className="mt-3 text-center">
                                        <span className="text-lg font-semibold text-neon-cyan">
                                            {Math.round(progress)}%
                                        </span>
                                    </div>
                                </div>

                                <p className="text-center text-sm text-gray-400 animate-pulse">
                                    Crafting plot twists and characters with AI magic ✨
                                </p>
                            </div>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <Select
                                    label="Target Language"
                                    name="language"
                                    value={formData.language}
                                    onChange={handleChange}
                                    options={[
                                        { value: 'Spanish', label: 'Spanish' },
                                        { value: 'French', label: 'French' },
                                        { value: 'German', label: 'German' },
                                        { value: 'Italian', label: 'Italian' },
                                        { value: 'Japanese', label: 'Japanese' },
                                        { value: 'Chinese', label: 'Chinese' },
                                    ]}
                                />
                                <Select
                                    label="Language Level"
                                    name="level"
                                    value={formData.level}
                                    onChange={handleChange}
                                    options={[
                                        { value: 'A1', label: 'A1 - Beginner' },
                                        { value: 'A2', label: 'A2 - Elementary' },
                                        { value: 'B1', label: 'B1 - Intermediate' },
                                        { value: 'B2', label: 'B2 - Upper Intermediate' },
                                        { value: 'C1', label: 'C1 - Advanced' },
                                    ]}
                                />
                                <Select
                                    label="Genre"
                                    name="genre"
                                    value={formData.genre}
                                    onChange={handleChange}
                                    options={[
                                        { value: 'fantasy', label: 'Fantasy' },
                                        { value: 'sci-fi', label: 'Sci-Fi' },
                                        { value: 'adventure', label: 'Adventure' },
                                        { value: 'mystery', label: 'Mystery' },
                                        { value: 'slice-of-life', label: 'Slice of Life' },
                                    ]}
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-300">Story Prompt</label>
                                <textarea
                                    name="prompt"
                                    value={formData.prompt}
                                    onChange={handleChange}
                                    rows={5}
                                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-neon-purple/50 focus:border-neon-purple/50 transition-all resize-none backdrop-blur"
                                    placeholder="Describe what you want the story to be about... (e.g., A young wizard discovering their magical powers in a hidden academy)"
                                    required
                                />
                            </div>

                            <button
                                type="submit"
                                className="w-full relative group overflow-hidden rounded-xl bg-gradient-to-r from-neon-purple to-neon-cyan p-[2px] transition-all hover:scale-[1.02] active:scale-[0.98]"
                            >
                                <div className="relative bg-dark-900 rounded-[10px] px-6 py-4 flex items-center justify-center gap-2 group-hover:bg-transparent transition-all">
                                    <Sparkles className="w-5 h-5 text-white" />
                                    <span className="font-semibold text-lg text-white">Generate Story</span>
                                </div>
                            </button>
                        </form>
                    )}
                </div>
            </div>
        </div>
    );
};
