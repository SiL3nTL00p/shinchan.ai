import React from 'react';

interface Props {
    onExampleClick: (query: string) => void;
}

const EXAMPLES = [
    'What is the overall failure rate for bill payments?',
    'Which payment networks have the highest failure rates?',
    'Show me transaction trends by hour of day',
    'What are the top 5 error codes causing failures?',
];

export default function WelcomeScreen({ onExampleClick }: Props) {
    return (
        <div className="flex flex-col items-center justify-center flex-1 px-6 text-center">
            <div className="mb-8">
                <h2 className="text-3xl font-bold tracking-tight mb-2">Shinchan AI</h2>
                <p className="text-white/40 text-sm max-w-md">
                    Conversational analytics engine for digital payments. Ask questions
                    about your transaction data in plain English.
                </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl w-full">
                {EXAMPLES.map((q) => (
                    <button
                        key={q}
                        onClick={() => onExampleClick(q)}
                        className="text-left text-sm text-white/60 bg-[#1C1C1E] hover:bg-[#2C2C2E] rounded-xl px-4 py-3 transition-colors border border-white/5 hover:border-white/10"
                    >
                        {q}
                    </button>
                ))}
            </div>
        </div>
    );
}
