import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown"

export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
    files?: File[];
}

interface ChatMessageProps {
    message: Message;
    isLatest?: boolean;
    isLoading?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, isLatest = false, isLoading = false }) => {
    const isUser = message.role === "user";

    return (
        <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{
                duration: 0.3,
                ease: [0.25, 0.1, 0.25, 1],
            }}
            className={cn(
                "flex gap-3 mb-6 group",
                isUser ? "justify-end" : "justify-start"
            )}
        >
            {/* Avatar — AI only */}
            {!isUser && (
                <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
                    className="flex-shrink-0 self-end"
                >
                    <div className="w-9 h-9 rounded-full bg-white flex items-center justify-center shadow-[0_0_12px_rgba(255,255,255,0.3),0_0_24px_rgba(255,255,255,0.1)]">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" className="text-black">
                            <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" stroke="currentColor">
                                <path d="M9,1.75C4.996,1.75,1.75,4.996,1.75,9c0,1.319,.358,2.552,.973,3.617,.43,.806-.053,2.712-.973,3.633,1.25,.068,2.897-.497,3.633-.973,.489,.282,1.264,.656,2.279,.848,.433,.082,.881,.125,1.338,.125,4.004,0,7.25-3.246,7.25-7.25S13.004,1.75,9,1.75Z" />
                            </g>
                        </svg>
                    </div>
                </motion.div>
            )}

            {/* Bubble */}
            <div
                className={cn(
                    "max-w-[70%] rounded-[22px] px-4 py-2.5 shadow-sm",
                    isUser
                        ? "bg-[#3B82F6] text-white"
                        : "bg-[#2D2D2D]/70 text-white"
                )}
            >
                <div className="text-[15px] leading-relaxed break-words">
    {(() => {
        const lines = message.content.split('\n');
        const result: React.ReactElement[] = [];
        let tableRows: string[][] = [];

        const flushTable = (key: string) => {
            if (tableRows.length === 0) return;
            result.push(
                <div key={key} className="overflow-x-auto my-3 rounded-lg border border-[#444]">
                    <table className="border-collapse text-sm w-full">
                        <thead>
                            <tr>
                                {tableRows[0].map((cell, j) => (
                                    <th key={j} className="border border-[#555] bg-[#2a2a2a] px-4 py-2 text-left font-semibold text-white/90">
                                        {cell}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {tableRows.slice(1).map((row, i) => (
                                <tr key={i} className={i % 2 === 0 ? "bg-[#1e1e1e]" : "bg-[#252525]"}>
                                    {row.map((cell, j) => (
                                        <td key={j} className="border border-[#444] px-4 py-2 text-white/80">
                                            {cell}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            );
            tableRows = [];
        };

        lines.forEach((line, i) => {
            if (line.trim().startsWith('|')) {
                if (line.match(/^\|[\s\-|]+\|?$/)) return;
                const cells = line.split('|').filter(c => c.trim() !== '').map(c => c.trim());
                tableRows.push(cells);
            } else {
                flushTable(`table-${i}`);
                if (line.trim()) result.push(<p key={i} className="mb-1 whitespace-pre-wrap">{line}</p>);
            }
        });
        flushTable('table-end');
        return result;
    })()}
</div>

                {/* Timestamp */}
                <div className="text-[11px] mt-1.5 opacity-50 text-white">
                    {message.timestamp.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                    })}
                </div>

                
            </div>

            {/* Avatar — User only */}
            {isUser && (
                <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
                    className="flex-shrink-0 self-end"
                >
                    <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center shadow-lg">
                        <svg className="w-5 h-5 text-[#1F2023]" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                        </svg>
                    </div>
                </motion.div>
            )}
        </motion.div>
    );
};
