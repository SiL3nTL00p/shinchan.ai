import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface PromptInputBoxProps {
    onSend: (message: string, files?: File[]) => void;
    isLoading?: boolean;
    placeholder?: string;
}

export const PromptInputBox: React.FC<PromptInputBoxProps> = ({
    onSend,
    isLoading = false,
    placeholder = "Type your message here...",
}) => {
    const [value, setValue] = useState("");
    const [files, setFiles] = useState<File[]>([]);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
        }
    }, [value]);

    const handleSubmit = () => {
        const trimmed = value.trim();
        if ((!trimmed && files.length === 0) || isLoading) return;
        onSend(trimmed, files.length > 0 ? files : undefined);
        setValue("");
        setFiles([]);
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setFiles(Array.from(e.target.files));
        }
    };

    const removeFile = (index: number) => {
        setFiles((prev) => prev.filter((_, i) => i !== index));
    };

    return (
        <div className="w-full">
            {/* File Previews */}
            <AnimatePresence>
                {files.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="flex gap-2 mb-2 flex-wrap"
                    >
                        {files.map((file, i) => (
                            <motion.div
                                key={i}
                                initial={{ scale: 0.8, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                exit={{ scale: 0.8, opacity: 0 }}
                                className="flex items-center gap-1.5 bg-[#2E3033] rounded-lg px-2.5 py-1.5 text-xs text-gray-300 border border-[#444444]"
                            >
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32" /></svg>
                                <span className="max-w-[120px] truncate">{file.name}</span>
                                <button
                                    onClick={() => removeFile(i)}
                                    className="ml-1 text-gray-500 hover:text-white transition-colors"
                                >
                                    ×
                                </button>
                            </motion.div>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Unified Dark Input Box */}
            <div className="bg-[#1F2023] border border-[#4a4a4c] rounded-[22px] shadow-2xl overflow-hidden">
                {/* Hidden file input */}
                <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    onChange={handleFileChange}
                    className="hidden"
                    accept="image/*,.pdf,.doc,.docx,.txt,.csv"
                />

                {/* Textarea */}
                <div className="px-5 pt-4 pb-2">
                    <textarea
                        ref={textareaRef}
                        value={value}
                        onChange={(e) => setValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                        placeholder={placeholder}
                        rows={1}
                        className="w-full resize-none bg-transparent text-white text-[15px] outline-none placeholder:text-gray-500 disabled:opacity-50 leading-relaxed"
                    />
                </div>

                {/* Bottom Toolbar */}
                <div className="flex items-center justify-between px-4 pb-3 pt-1">
                    {/* Settings Icon + Model Name Badge */}
                    <div className="flex items-center gap-2">
                        <button className="p-1.5 text-gray-400 transition-colors rounded-lg ">
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18">
                                <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" stroke="currentColor">
                                    <path d="M13.974,9.731c-.474,3.691-3.724,4.113-6.974,3.519" />
                                    <path d="M3.75,16.25S5.062,4.729,16.25,3.75c-.56,.976-.573,2.605-.946,4.239-.524,2.011-2.335,2.261-4.554,2.261" />
                                    <line x1="4.25" y1="1.75" x2="4.25" y2="6.75" />
                                    <line x1="6.75" y1="4.25" x2="1.75" y2="4.25" />
                                </g>
                            </svg>
                        </button>
                        <span className="text-[11px] text-gray-400 bg-[#2A2B2E] border border-[#3A3A3D] rounded-md px-2 py-0.5 font-mono">
                            llama-3.3-70b
                        </span>
                    </div>

                    {/* Send Button */}
                    <button
                        onClick={handleSubmit}
                        disabled={isLoading || (!value.trim() && files.length === 0)}
                        className="flex items-center justify-center w-8 h-8 rounded-full bg-white text-black hover:bg-gray-100 transition-all duration-200 shadow-lg cursor-pointer disabled:cursor-not-allowed disabled:bg-white disabled:text-black disabled:opacity-100"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
};
