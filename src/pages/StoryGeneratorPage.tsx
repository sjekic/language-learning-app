import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Select } from '../components/Select';
import { Sparkles } from 'lucide-react';

export const StoryGeneratorPage: React.FC = () => {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = useState(false);
    const [formData, setFormData] = useState({
        level: 'B1',
        genre: 'fantasy',
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
                content: `This is page ${i + 1} of the story about ${formData.prompt || 'a mysterious adventure'}. The hero walked through the ${formData.genre} world, looking for clues. Suddenly, a strange creature appeared! It was a moment of truth. The wind howled, and the sky turned purple. "What is happening?" asked the hero.`,
            }));

            navigate('/read', { state: { story: mockStory, title: formData.prompt || 'My AI Story' } });
        }, 2000);
    };

    return (
        <div className="max-w-2xl mx-auto py-12">
            <div className="text-center mb-10">
                <div className="inline-flex items-center justify-center p-3 bg-primary-100 rounded-2xl mb-4">
                    <Sparkles className="w-8 h-8 text-primary-600" />
                </div>
                <h1 className="text-3xl font-bold text-gray-900">Create Your AI Story</h1>
                <p className="mt-3 text-gray-600">
                    This will generate a 10-page story based on your level, genre, and prompt.
                </p>
            </div>

            <div className="bg-white rounded-2xl shadow-xl shadow-gray-200/50 border border-gray-100 p-8">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-12 space-y-4">
                        <div className="relative">
                            <div className="w-16 h-16 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <Sparkles className="w-6 h-6 text-primary-600 animate-pulse" />
                            </div>
                        </div>
                        <p className="text-lg font-medium text-gray-700 animate-pulse">Creating your story...</p>
                        <p className="text-sm text-gray-500">Crafting plot twists and characters</p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                            <label className="text-sm font-medium text-gray-700">Story Prompt</label>
                            <textarea
                                name="prompt"
                                value={formData.prompt}
                                onChange={handleChange}
                                rows={4}
                                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 shadow-sm hover:border-gray-300 transition-all resize-none"
                                placeholder="Describe what you want the story to be about... (e.g., A young wizard learning to fly)"
                                required
                            />
                        </div>

                        <Button type="submit" className="w-full" size="lg">
                            Generate Story
                        </Button>
                    </form>
                )}
            </div>
        </div>
    );
};
