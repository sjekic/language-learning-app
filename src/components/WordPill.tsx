import React from 'react';
import { cn } from '../lib/utils';
import { X } from 'lucide-react';

interface WordPillProps {
    word: string;
    onRemove?: () => void;
}

export const WordPill: React.FC<WordPillProps> = ({ word, onRemove }) => {
    return (
        <div className="inline-flex items-center px-3 py-1 rounded-full bg-primary-50 text-primary-700 text-sm font-medium border border-primary-100 shadow-sm animate-in fade-in zoom-in duration-200">
            <span>{word}</span>
            {onRemove && (
                <button
                    onClick={onRemove}
                    className="ml-2 p-0.5 rounded-full hover:bg-primary-100 text-primary-400 hover:text-primary-600 transition-colors"
                >
                    <X className="w-3 h-3" />
                </button>
            )}
        </div>
    );
};
