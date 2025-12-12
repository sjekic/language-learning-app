import React, { useState, useEffect } from 'react';
import { getSavedWords, deleteSavedWord, type SavedWord } from '../lib/vocabulary';
import { BookOpen, Trash2, Download, Filter, Search } from 'lucide-react';

export const VocabularyPage: React.FC = () => {
    const [words, setWords] = useState<SavedWord[]>([]);
    const [filteredWords, setFilteredWords] = useState<SavedWord[]>([]);
    const [selectedLanguage, setSelectedLanguage] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // Load words on mount
    useEffect(() => {
        loadWords();
    }, []);

    // Filter words when search or language filter changes
    useEffect(() => {
        let filtered = words;

        // Filter by language
        if (selectedLanguage !== 'all') {
            filtered = filtered.filter(w => w.sourceLanguage === selectedLanguage);
        }

        // Filter by search query
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            filtered = filtered.filter(
                w => w.word.toLowerCase().includes(query) ||
                    w.translation.toLowerCase().includes(query)
            );
        }

        setFilteredWords(filtered);
    }, [words, selectedLanguage, searchQuery]);

    const loadWords = async () => {
        setIsLoading(true);
        try {
            const savedWords = await getSavedWords();
            setWords(savedWords);
        } finally {
            setIsLoading(false);
        }
    };

    const handleDelete = async (id: string) => {
        await deleteSavedWord(id);
        await loadWords();
    };

    const handleExport = () => {
        const dataStr = JSON.stringify(words, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `vocabulary-${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        URL.revokeObjectURL(url);
    };

    // Get unique languages from saved words
    const languages = Array.from(new Set(words.map(w => w.sourceLanguage)));

    return (
        <div className="min-h-screen bg-dark-900 py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-5xl mx-auto space-y-8">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-gradient-to-br from-neon-purple to-neon-cyan rounded-xl">
                            <BookOpen className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold text-white">My Vocabulary</h1>
                            <p className="text-sm text-gray-400 mt-1">
                                {filteredWords.length} {filteredWords.length === 1 ? 'word' : 'words'} saved
                            </p>
                        </div>
                    </div>

                    {words.length > 0 && (
                        <button
                            onClick={handleExport}
                            className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-white hover:bg-white/10 transition-all"
                        >
                            <Download className="w-4 h-4" />
                            Export
                        </button>
                    )}
                </div>

                {/* Filters */}
                {words.length > 0 && (
                    <div className="glass-dark rounded-xl border border-white/10 p-6 space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Search */}
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                <input
                                    type="text"
                                    placeholder="Search words..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full pl-10 pr-4 py-2.5 bg-dark-800 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-neon-purple/50 transition-colors"
                                />
                            </div>

                            {/* Language Filter */}
                            <div className="relative">
                                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                <select
                                    value={selectedLanguage}
                                    onChange={(e) => setSelectedLanguage(e.target.value)}
                                    className="w-full pl-10 pr-4 py-2.5 bg-dark-800 border border-white/10 rounded-lg text-white focus:outline-none focus:border-neon-purple/50 transition-colors appearance-none cursor-pointer"
                                >
                                    <option value="all">All Languages</option>
                                    {languages.map(lang => (
                                        <option key={lang} value={lang}>{lang}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    </div>
                )}

                {/* Words List */}
                    {isLoading ? (
                        <div className="glass-dark rounded-2xl border border-white/10 p-12 text-center">
                            <p className="text-gray-400">Loading vocabulary…</p>
                        </div>
                    ) : filteredWords.length === 0 ? (
                    <div className="glass-dark rounded-2xl border border-white/10 p-12 text-center">
                        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-neon-purple/10 flex items-center justify-center">
                            <BookOpen className="w-8 h-8 text-neon-purple" />
                        </div>
                        <h3 className="text-xl font-semibold text-white mb-2">
                            {searchQuery || selectedLanguage !== 'all'
                                ? 'No words match your filters'
                                : 'No saved words yet'}
                        </h3>
                        <p className="text-gray-400 mb-6">
                            {searchQuery || selectedLanguage !== 'all'
                                ? 'Try adjusting your search or filters'
                                : 'Start reading stories and save words to build your vocabulary!'}
                        </p>
                    </div>
                ) : (
                    <div className="grid gap-4">
                        {filteredWords.map((wordItem) => (
                            <div
                                key={wordItem.id}
                                className="glass-dark rounded-xl border border-white/10 p-6 hover:border-neon-purple/30 transition-all group"
                            >
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex-1 space-y-2">
                                        {/* Word and Translation */}
                                        <div className="flex items-baseline gap-3 flex-wrap">
                                            <span className="text-2xl font-bold text-white">
                                                {wordItem.word}
                                            </span>
                                            <span className="text-gray-400">→</span>
                                            <span className="text-xl font-medium text-neon-cyan">
                                                {wordItem.translation}
                                            </span>
                                        </div>

                                        {/* Metadata */}
                                        <div className="flex items-center gap-4 text-sm text-gray-400">
                                            <span className="px-2 py-1 bg-neon-purple/10 text-neon-purple rounded-md border border-neon-purple/20">
                                                {wordItem.partOfSpeech}
                                            </span>
                                            <span className="flex items-center gap-1.5">
                                                <span className="w-1.5 h-1.5 rounded-full bg-gray-600"></span>
                                                {wordItem.sourceLanguage}
                                            </span>
                                            <span className="flex items-center gap-1.5">
                                                <span className="w-1.5 h-1.5 rounded-full bg-gray-600"></span>
                                                {new Date(wordItem.savedAt).toLocaleDateString()}
                                            </span>
                                        </div>

                                        {/* Context (if available) */}
                                        {wordItem.context && (
                                            <p className="text-sm text-gray-500 italic mt-2 pl-4 border-l-2 border-white/10">
                                                "{wordItem.context}"
                                            </p>
                                        )}
                                    </div>

                                    {/* Delete Button */}
                                    <button
                                        onClick={() => handleDelete(wordItem.id)}
                                        className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                                        title="Delete word"
                                    >
                                        <Trash2 className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
