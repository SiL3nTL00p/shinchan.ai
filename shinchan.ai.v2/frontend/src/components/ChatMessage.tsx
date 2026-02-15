import React from 'react';
import type { ChatMessage as ChatMessageType } from '../types';
import Spinner from './Spinner';
import MessageStats from './MessageStats';

interface Props {
    message: ChatMessageType;
}

export default function ChatMessage({ message }: Props) {
    const isUser = message.role === 'user';

    if (message.isLoading) {
        return (
            <div className="flex justify-start mb-3 message-enter">
                <div className="max-w-[75%] rounded-2xl bg-[#2C2C2E] rounded-bl-md">
                    <Spinner />
                </div>
            </div>
        );
    }

    return (
        <div
            className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3 message-enter`}
        >
            <div
                className={`max-w-[75%] px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap ${isUser
                        ? 'bg-[#0A84FF] text-white rounded-2xl rounded-br-md'
                        : 'bg-[#2C2C2E] text-white/90 rounded-2xl rounded-bl-md'
                    }`}
            >
                {message.content}
                {!isUser && message.response && !message.response.error && (
                    <MessageStats response={message.response} />
                )}
            </div>
        </div>
    );
}
