import React, { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChatMessage, Message } from "./chat-message";
import { cn } from "@/lib/utils";

interface ChatContainerProps {
    messages: Message[];
    isLoading?: boolean;
    className?: string;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
    messages,
    isLoading = false,
    className,
}) => {
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    return (
        <div
            ref={containerRef}
            className={cn(
                "flex-1 overflow-y-auto overflow-x-hidden px-4 py-6",
                "scrollbar-thin scrollbar-thumb-[#444444] scrollbar-track-transparent",
                className
            )}
        >
            {/* Empty State */}
            {messages.length === 0 && !isLoading && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col items-center justify-center h-full text-center"
                >
                    <motion.div
                        animate={{
                            scale: [1, 1.05, 1],
                            rotate: [0, 5, -5, 0],
                        }}
                        transition={{
                            duration: 4,
                            repeat: Infinity,
                            ease: "easeInOut",
                        }}
                        className="w-20 h-20 rounded-full bg-white flex items-center justify-center mb-6 shadow-2xl"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 18 18" className="text-black">
                            <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" stroke="currentColor">
                                <path d="M1.75,5.75l6.767,3.733c.301,.166,.665,.166,.966,0l6.767-3.733" />
                                <rect x="1.75" y="3.25" width="14.5" height="11.5" rx="2" ry="2" transform="translate(18 18) rotate(180)" />
                            </g>
                        </svg>
                    </motion.div>
                    <h2 className="text-2xl font-semibold text-white/90 mb-2">
                        Start a conversation
                    </h2>
                    <p className="text-white/60 max-w-md">
                        Send a message to begin chatting with the AI assistant
                    </p>
                </motion.div>
            )}

            {/* Messages */}
            <AnimatePresence mode="popLayout">
                {messages.map((message, index) => (
                    <ChatMessage
                        key={message.id}
                        message={message}
                        isLatest={index === messages.length - 1 && message.role === "assistant"}
                    />
                ))}
            </AnimatePresence>

            {/* Loading Indicator */}
            {isLoading && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="flex gap-3 mb-6"
                >
                    <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center shadow-lg">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 18 18" className="text-black animate-spin">
                            <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" stroke="currentColor">
                                <path d="M9,1.75C4.996,1.75,1.75,4.996,1.75,9c0,1.319,.358,2.552,.973,3.617,.43,.806-.053,2.712-.973,3.633,1.25,.068,2.897-.497,3.633-.973,.489,.282,1.264,.656,2.279,.848,.433,.082,.881,.125,1.338,.125,4.004,0,7.25-3.246,7.25-7.25S13.004,1.75,9,1.75Z" />
                            </g>
                        </svg>
                    </div>
                    <div className="bg-[#2E3033] rounded-2xl rounded-bl-md px-4 py-3 border border-[#444444] shadow-lg">
                        <div className="flex gap-1">
                            {[0, 1, 2].map((i) => (
                                <motion.div
                                    key={i}
                                    animate={{
                                        scale: [1, 1.3, 1],
                                        opacity: [0.5, 1, 0.5],
                                    }}
                                    transition={{
                                        duration: 1,
                                        repeat: Infinity,
                                        delay: i * 0.2,
                                    }}
                                    className="w-2 h-2 rounded-full bg-[#8B5CF6]"
                                />
                            ))}
                        </div>
                    </div>
                </motion.div>
            )}

            {/* Scroll Anchor */}
            <div ref={messagesEndRef} />
        </div>
    );
};
