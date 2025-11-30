import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Select } from '../components/Select';
import { Sparkles } from 'lucide-react';
import { saveStory } from '../lib/storage';

export const StoryGeneratorPage: React.FC = () => {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = useState(false);
    const [formData, setFormData] = useState({
        level: 'B1',
        genre: 'fantasy',
        language: 'Spanish',
        prompt: '',
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        // Mock AI Generation
        setTimeout(() => {
            setIsLoading(false);
            // Mock story data
            const mockStory = Array.from({ length: 10 }, (_, i) => ({
                id: i + 1,
                content: `This is page ${i + 1} of the story about ${formData.prompt || 'a mysterious adventure'} in ${formData.language}. The hero walked through the ${formData.genre} world, looking for clues. Suddenly, a strange creature appeared! It was a moment of truth. The wind howled, and the sky turned purple. "What is happening?" asked the hero.`,
            }));

            // Save to localStorage
            saveStory({
                title: formData.prompt || 'My AI Story',
                language: formData.language,
                level: formData.level,
                genre: formData.genre,
                pages: mockStory,
            });

            navigate('/read', { state: { story: mockStory, title: formData.prompt || 'My AI Story' } });
        }, 2000);
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
                        <div className="flex flex-col items-center justify-center py-16 space-y-6">
                            <div className="relative">
                                <div className="w-20 h-20 border-4 border-white/10 border-t-neon-purple rounded-full animate-spin"></div>
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <Sparkles className="w-8 h-8 text-neon-purple animate-pulse" />
                                </div>
                            </div>
                            <p className="text-xl font-semibold text-white animate-pulse">Creating your story...</p>
                            <p className="text-sm text-gray-400">Crafting plot twists and characters with AI magic ✨</p>
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
