/** @type {import('tailwindcss').Config} */
export default {
    content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
    theme: {
        extend: {
            colors: {
                primary: '#0A84FF',
                bubble: {
                    user: '#0A84FF',
                    ai: '#2C2C2E',
                },
                surface: '#1C1C1E',
                background: '#000000',
            },
            fontFamily: {
                sans: [
                    '-apple-system',
                    'BlinkMacSystemFont',
                    'SF Pro Text',
                    'Segoe UI',
                    'Roboto',
                    'Helvetica Neue',
                    'sans-serif',
                ],
            },
        },
    },
    plugins: [],
};
