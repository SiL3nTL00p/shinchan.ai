import React from 'react';

interface HeaderProps {
    onClear: () => void;
    messageCount: number;
}

export default function Header({ onClear, messageCount }: HeaderProps) {
    return (
        <header className="flex items-center justify-between px-5 py-3 border-b border-white/10 bg-black/80 backdrop-blur-xl z-10">
            <div className="flex items-center gap-3">
                {/* Traffic lights */}
                <div className="flex gap-2 mr-2">
                    <span className="w-3 h-3 rounded-full bg-[#FF5F57]" />
                    <span className="w-3 h-3 rounded-full bg-[#FEBC2E]" />
                    <span className="w-3 h-3 rounded-full bg-[#28C840]" />
                </div>
                <h1 className="text-base font-semibold tracking-tight">shinchan AI</h1>
                <span className="text-xs text-white/40 ml-1">analytics</span>
            </div>
            <div className="flex items-center gap-3">
                {messageCount > 0 && (
                    <button
                        onClick={onClear}
                        className="text-xs text-white/50 hover:text-white/80 transition-colors px-3 py-1 rounded-lg hover:bg-white/5"
                    >
                        Clear
                    </button>
                )}
            </div>
        </header>
    );
}
