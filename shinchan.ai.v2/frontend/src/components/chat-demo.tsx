import React, { useState, useEffect } from "react";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { ChatContainer } from "@/components/ui/chat-container";
import { Message } from "@/components/ui/chat-message";
import { ConversationSidebar, Conversation } from "@/components/ui/conversation-sidebar";
import { SidebarToggle } from "@/components/ui/sidebar-toggle";
import { sendQuery } from "@/services/api";
import { motion } from "framer-motion";

interface ConversationData {
    id: string;
    messages: Message[];
    title: string;
    createdAt: Date;
    updatedAt: Date;
}

const DemoOne = () => {
    const [conversations, setConversations] = useState<ConversationData[]>([]);
    const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    // Get current conversation
    const currentConversation = conversations.find(
        (c) => c.id === currentConversationId
    );
    const currentMessages = currentConversation?.messages || [];

    // Generate conversation title from first message
    const generateTitle = (firstMessage: string): string => {
        const maxLength = 40;
        if (firstMessage.length <= maxLength) return firstMessage;
        return firstMessage.substring(0, maxLength) + "...";
    };

    // Create new conversation
    const createNewConversation = () => {
        const newConversation: ConversationData = {
            id: Date.now().toString(),
            messages: [],
            title: "New Conversation",
            createdAt: new Date(),
            updatedAt: new Date(),
        };
        setConversations((prev) => [newConversation, ...prev]);
        setCurrentConversationId(newConversation.id);
    };

    // Initialize with first conversation
    useEffect(() => {
        if (conversations.length === 0) {
            createNewConversation();
        }
    }, []);

    // Load from localStorage on mount
    useEffect(() => {
        const saved = localStorage.getItem("shinchan_conversations");
        const savedId = localStorage.getItem("shinchan_current_id");
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                const restored = parsed.map((conv: any) => ({
                    ...conv,
                    createdAt: new Date(conv.createdAt),
                    updatedAt: new Date(conv.updatedAt),
                    messages: conv.messages.map((msg: any) => ({
                        ...msg,
                        timestamp: new Date(msg.timestamp),
                    })),
                }));
                setConversations(restored);
                if (savedId && restored.find((c: any) => c.id === savedId)) {
                    setCurrentConversationId(savedId);
                } else if (restored.length > 0) {
                    setCurrentConversationId(restored[0].id);
                }
            } catch {
                // ignore corrupt data
            }
        }
    }, []);

    // Save conversations to localStorage
    useEffect(() => {
        if (conversations.length > 0) {
            localStorage.setItem("shinchan_conversations", JSON.stringify(conversations));
        }
    }, [conversations]);

    useEffect(() => {
        if (currentConversationId) {
            localStorage.setItem("shinchan_current_id", currentConversationId);
        }
    }, [currentConversationId]);

    // Handle sending message
    const handleSendMessage = async (message: string, files?: File[]) => {
        if (!currentConversationId) {
            createNewConversation();
            return;
        }

        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: message,
            timestamp: new Date(),
            files,
        };

        setConversations((prev) =>
            prev.map((conv) => {
                if (conv.id === currentConversationId) {
                    return {
                        ...conv,
                        messages: [...conv.messages, userMessage],
                        title: conv.messages.length === 0 ? generateTitle(message) : conv.title,
                        updatedAt: new Date(),
                    };
                }
                return conv;
            })
        );

        setIsLoading(true);

        try {
            const response = await sendQuery(message);

            const aiMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: response.insight,
                timestamp: new Date(),
            };

            setConversations((prev) =>
                prev.map((conv) => {
                    if (conv.id === currentConversationId) {
                        return {
                            ...conv,
                            messages: [...conv.messages, aiMessage],
                            updatedAt: new Date(),
                        };
                    }
                    return conv;
                })
            );
        } catch (error) {
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: "Something went wrong. Please try again.",
                timestamp: new Date(),
            };
            setConversations((prev) =>
                prev.map((conv) => {
                    if (conv.id === currentConversationId) {
                        return {
                            ...conv,
                            messages: [...conv.messages, errorMessage],
                            updatedAt: new Date(),
                        };
                    }
                    return conv;
                })
            );
        } finally {
            setIsLoading(false);
        }
    };

    // Select conversation
    const handleSelectConversation = (id: string) => {
        setCurrentConversationId(id);
    };

    // Delete conversation
    const handleDeleteConversation = (id: string) => {
        setConversations((prev) => {
            const filtered = prev.filter((c) => c.id !== id);
            if (id === currentConversationId) {
                if (filtered.length > 0) {
                    setCurrentConversationId(filtered[0].id);
                } else {
                    const newConv: ConversationData = {
                        id: Date.now().toString(),
                        messages: [],
                        title: "New Conversation",
                        createdAt: new Date(),
                        updatedAt: new Date(),
                    };
                    setCurrentConversationId(newConv.id);
                    return [newConv];
                }
            }
            return filtered;
        });
    };

    // Convert to sidebar format
    const sidebarConversations: Conversation[] = conversations.map((conv) => ({
        id: conv.id,
        title: conv.title,
        preview: conv.messages[conv.messages.length - 1]?.content || "No messages yet",
        timestamp: conv.updatedAt,
        messageCount: conv.messages.length,
    }));

    return (
        <div className="flex w-full h-screen justify-center items-center bg-[radial-gradient(125%_125%_at_50%_101%,rgba(245,87,2,1)_10.5%,rgba(245,120,2,1)_16%,rgba(245,140,2,1)_17.5%,rgba(245,170,100,1)_25%,rgba(238,174,202,1)_40%,rgba(202,179,214,1)_65%,rgba(148,201,233,1)_100%)]">
            {/* Conversation Sidebar */}
            <ConversationSidebar
                isOpen={isSidebarOpen}
                onClose={() => setIsSidebarOpen(false)}
                conversations={sidebarConversations}
                currentConversationId={currentConversationId}
                onSelectConversation={handleSelectConversation}
                onNewConversation={createNewConversation}
                onDeleteConversation={handleDeleteConversation}
            />

            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3 }}
                className="w-full max-w-4xl h-[85vh] mx-4"
            >
                <div className="h-full flex flex-col gap-3">
                    {/* Conversation History Shell */}
                    <div className="flex-1 min-h-0 rounded-[22px] bg-[#1F2023] border border-[#4a4a4c] shadow-2xl flex flex-col overflow-hidden">
                        {/* Menu Icon */}
                        <div className="px-5 py-4">
                            <SidebarToggle onClick={() => setIsSidebarOpen(true)} />
                        </div>

                        {/* Messages */}
                        <ChatContainer messages={currentMessages} isLoading={isLoading} />
                    </div>

                    {/* Separate Input Box — narrower than convo box */}
                    <motion.div
                        initial={{ y: 20, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        transition={{ delay: 0.2 }}
                        className="flex-shrink-0 mx-auto w-full" style={{ maxWidth: 500 }}
                    >
                        <PromptInputBox
                            onSend={handleSendMessage}
                            isLoading={isLoading}
                            placeholder="Ask about your transaction data..."
                        />
                    </motion.div>
                </div>
            </motion.div>
        </div>
    );
};

export { DemoOne };
