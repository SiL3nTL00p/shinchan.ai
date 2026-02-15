import { useState, useCallback } from 'react';
import type { QueryResponse } from '../types';

type Status = 'idle' | 'loading' | 'success' | 'error';

export function useAPI<T>(apiCall: (...args: any[]) => Promise<T>) {
    const [data, setData] = useState<T | null>(null);
    const [status, setStatus] = useState<Status>('idle');
    const [error, setError] = useState<string | null>(null);

    const execute = useCallback(
        async (...args: any[]) => {
            setStatus('loading');
            setError(null);
            try {
                const result = await apiCall(...args);
                setData(result);
                setStatus('success');
                return result;
            } catch (err: any) {
                const msg = err?.message || 'An error occurred';
                setError(msg);
                setStatus('error');
                throw err;
            }
        },
        [apiCall]
    );

    const reset = useCallback(() => {
        setData(null);
        setStatus('idle');
        setError(null);
    }, []);

    return { data, status, error, execute, reset, isLoading: status === 'loading' };
}
