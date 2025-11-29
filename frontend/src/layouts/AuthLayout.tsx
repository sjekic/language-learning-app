import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sparkles } from 'lucide-react';

export const AuthLayout: React.FC = () => {
    return (
        <div className="min-h-screen bg-dark-900 relative overflow-hidden flex items-center justify-center p-4">
            {/* Cosmic Gradient Background */}
            <div className="absolute inset-0 bg-gradient-cosmic" />

            {/* Animated Glowing Spheres - 3D Orbital Effect */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                {/* Large Main Sphere */}
                <div className="absolute w-96 h-96 rounded-full gradient-sphere blur-3xl opacity-40 animate-pulse-glow" />

                {/* Orbital Ring */}
                <div className="absolute w-[500px] h-[500px] rounded-full border border-neon-purple/20" />
                <div className="absolute w-[450px] h-[450px] rounded-full border border-neon-cyan/10 animate-spin" style={{ animationDuration: '30s' }} />

                {/* Small Orbiting Particles */}
                <div className="absolute w-4 h-4 rounded-full bg-neon-purple glow-purple animate-orbit" />
                <div className="absolute w-3 h-3 rounded-full bg-neon-cyan glow-cyan animate-orbit" style={{ animationDelay: '5s', animationDuration: '15s' }} />
                <div className="absolute w-2 h-2 rounded-full bg-neon-pink animate-orbit" style={{ animationDelay: '10s', animationDuration: '25s' }} />
            </div>

            {/* Logo/Brand */}
            <div className="absolute top-8 left-1/2 -translate-x-1/2 flex items-center gap-2 z-10">
                <div className="bg-neon-purple/10 p-2 rounded-lg backdrop-blur-sm border border-neon-purple/20">
                    <Sparkles className="w-6 h-6 text-neon-purple" />
                </div>
                <h1 className="text-2xl font-bold text-white">StoryAI</h1>
            </div>

            {/* Auth Content */}
            <div className="relative z-10 w-full max-w-md">
                <div className="glass-dark rounded-3xl p-8 sm:p-10 relative overflow-hidden">
                    {/* Inner Glow */}
                    <div className="absolute inset-0 bg-gradient-radial from-neon-purple/5 to-transparent opacity-50" />

                    <div className="relative z-10">
                        <Outlet />
                    </div>
                </div>
            </div>
        </div>
    );
};
