import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/Button';
import { Input } from '../components/Input';

export const SignupPage: React.FC = () => {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = React.useState(false);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        // Mock signup
        setTimeout(() => {
            setIsLoading(false);
            navigate('/generate');
        }, 1000);
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-gray-900 text-center">Create Account</h2>
                <p className="mt-2 text-center text-sm text-gray-600">
                    Start creating amazing stories today
                </p>
            </div>

            <form className="space-y-6" onSubmit={handleSubmit}>
                <Input
                    label="Username"
                    type="text"
                    placeholder="StoryTeller"
                    required
                />
                <Input
                    label="Email address"
                    type="email"
                    placeholder="you@example.com"
                    required
                />
                <Input
                    label="Password"
                    type="password"
                    placeholder="••••••••"
                    required
                />

                <Button type="submit" className="w-full" isLoading={isLoading}>
                    Sign Up
                </Button>
            </form>

            <div className="text-center text-sm">
                <span className="text-gray-500">Already have an account? </span>
                <Link to="/login" className="font-medium text-primary-600 hover:text-primary-500">
                    Login
                </Link>
            </div>
        </div>
    );
};
