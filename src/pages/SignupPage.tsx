import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

export const SignupPage: React.FC = () => {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = React.useState(false);
    const [username, setUsername] = React.useState('');
    const [email, setEmail] = React.useState('');
    const [password, setPassword] = React.useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        // Mock signup
        setTimeout(() => {
            setIsLoading(false);
            navigate('/library');
        }, 1000);
    };

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="text-center">
                <h2 className="text-3xl font-bold text-white mb-2">
                    Elevate your thinking
                </h2>
                <p className="text-gray-400">
                    Discover endless ways language learning can enhance your journey
                </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
                {/* Username Input */}
                <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-300">
                        Username
                    </label>
                    <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-neon-purple/50 focus:border-neon-purple/50 transition-all"
                        placeholder="StoryTeller"
                        required
                    />
                </div>

                {/* Email Input */}
                <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-300">
                        Email address
                    </label>
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-neon-purple/50 focus:border-neon-purple/50 transition-all"
                        placeholder="you@example.com"
                        required
                    />
                </div>

                {/* Password Input */}
                <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-300">
                        Password
                    </label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-neon-purple/50 focus:border-neon-purple/50 transition-all"
                        placeholder="••••••••"
                        required
                    />
                </div>

                {/* Get Started Button */}
                <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full relative group overflow-hidden rounded-xl bg-gradient-to-r from-neon-purple to-neon-cyan p-[2px] transition-all hover:scale-[1.02] active:scale-[0.98]"
                >
                    <div className="relative bg-dark-900 rounded-[10px] px-6 py-3 flex items-center justify-center gap-2 group-hover:bg-transparent transition-all">
                        <span className={`font-semibold text-white ${isLoading ? 'opacity-50' : ''}`}>
                            {isLoading ? 'Creating account...' : 'Get Started'}
                        </span>
                        {!isLoading && <ArrowRight className="w-5 h-5 text-white group-hover:translate-x-1 transition-transform" />}
                    </div>
                </button>
            </form>

            {/* Login Link */}
            <div className="text-center text-sm">
                <span className="text-gray-400">Already have an account? </span>
                <Link to="/login" className="font-medium text-neon-purple hover:text-neon-cyan transition-colors">
                    Sign In
                </Link>
            </div>
        </div>
    );
};
