import { useState, useCallback, useRef } from 'react';
import type { ChatMessage, QueryResponse } from '../types';
import { sendQuery, clearConversation } from '../services/api';

let messageId = 0;
const nextId = () => `msg-${++messageId}`;

function generateConversationId() {
    return `conv-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function useChat() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const abortRef = useRef<AbortController | null>(null);
    const conversationIdRef = useRef<string>(generateConversationId());

    const addMessage = useCallback(
        (role: 'user' | 'assistant', content: string, response?: QueryResponse) => {
            const msg: ChatMessage = {
                id: nextId(),
                role,
                content,
                timestamp: new Date(),
                response,
            };
            setMessages((prev) => [...prev, msg]);
            return msg.id;
        },
        []
    );

    const send = useCallback(
        async (query: string) => {
            if (!query.trim() || isProcessing) return;

            // Add user message
            addMessage('user', query.trim());

            // Add placeholder assistant message
            const loadingId = nextId();
            setMessages((prev) => [
                ...prev,
                {
                    id: loadingId,
                    role: 'assistant',
                    content: '',
                    timestamp: new Date(),
                    isLoading: true,
                },
            ]);
            setIsProcessing(true);

            try {
                const response = await sendQuery(
                    query.trim(),
                    conversationIdRef.current
                );
                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === loadingId
                            ? {
                                ...m,
                                content: response.insight,
                                response,
                                isLoading: false,
                            }
                            : m
                    )
                );
            } catch (err: any) {
                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === loadingId
                            ? {
                                ...m,
                                content: 'Something went wrong. Please try again.',
                                isLoading: false,
                            }
                            : m
                    )
                );
            } finally {
                setIsProcessing(false);
            }
        },
        [isProcessing, addMessage]
    );

    const clear = useCallback(() => {
        clearConversation(conversationIdRef.current).catch(() => { });
        setMessages([]);
        conversationIdRef.current = generateConversationId();
    }, []);

    return { messages, isProcessing, send, clear };
}
