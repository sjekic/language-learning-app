import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/Button';
import { Input } from '../components/Input';

export const LoginPage: React.FC = () => {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = React.useState(false);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        // Mock login
        setTimeout(() => {
            setIsLoading(false);
            navigate('/generate');
        }, 1000);
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-gray-900 text-center">Welcome Back</h2>
                <p className="mt-2 text-center text-sm text-gray-600">
                    Sign in to continue your story journey
                </p>
            </div>

            <form className="space-y-6" onSubmit={handleSubmit}>
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
                    Login
                </Button>
            </form>

            <div className="text-center text-sm">
                <span className="text-gray-500">Don't have an account? </span>
                <Link to="/signup" className="font-medium text-primary-600 hover:text-primary-500">
                    Sign up
                </Link>
            </div>
        </div>
    );
};
