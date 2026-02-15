import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface SidebarToggleProps {
    onClick: () => void;
    className?: string;
}

export const SidebarToggle: React.FC<SidebarToggleProps> = ({
    onClick,
    className,
}) => {
    return (
        <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onClick}
            className={cn(
                "p-2 text-white/70 hover:text-white transition-colors",
                className
            )}
        >
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 18 18">
                <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" stroke="currentColor">
                    <line x1="2.25" y1="9" x2="15.75" y2="9" />
                    <line x1="2.25" y1="3.75" x2="15.75" y2="3.75" />
                    <line x1="2.25" y1="14.25" x2="15.75" y2="14.25" />
                </g>
            </svg>
        </motion.button>
    );
};
