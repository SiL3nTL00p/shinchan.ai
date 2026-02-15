import React from 'react';

export default function Spinner() {
    return (
        <div className="flex items-center gap-1.5 px-4 py-3">
            <span className="typing-dot w-2 h-2 rounded-full bg-white/60" />
            <span className="typing-dot w-2 h-2 rounded-full bg-white/60" />
            <span className="typing-dot w-2 h-2 rounded-full bg-white/60" />
        </div>
    );
}
