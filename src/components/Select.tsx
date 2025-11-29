import React from 'react';
import { cn } from '../lib/utils';
import { ChevronDown } from 'lucide-react';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
    label?: string;
    error?: string;
    options: { value: string; label: string }[];
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
    ({ className, label, error, options, ...props }, ref) => {
        return (
            <div className="w-full space-y-2">
                {label && (
                    <label className="text-sm font-medium text-gray-300 leading-none">
                        {label}
                    </label>
                )}
                <div className="relative">
                    <select
                        ref={ref}
                        className={cn(
                            'flex h-11 w-full appearance-none rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-white backdrop-blur focus:outline-none focus:ring-2 focus:ring-neon-purple/50 focus:border-neon-purple/50 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200',
                            error && 'border-red-500 focus:ring-red-500',
                            className
                        )}
                        {...props}
                    >
                        {options.map((option) => (
                            <option key={option.value} value={option.value} className="bg-dark-800 text-white">
                                {option.label}
                            </option>
                        ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-3 h-5 w-5 text-gray-400 pointer-events-none" />
                </div>
                {error && <p className="text-sm text-red-400">{error}</p>}
            </div>
        );
    }
);

Select.displayName = 'Select';
