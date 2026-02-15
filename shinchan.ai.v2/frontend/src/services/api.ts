import type { QueryResponse, SystemStats } from '../types';

const API_BASE = '/api';

export async function sendQuery(query: string, conversationId?: string): Promise<QueryResponse> {
    const res = await fetch(`${API_BASE}/chat/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, conversation_id: conversationId }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

export async function clearConversation(conversationId?: string): Promise<void> {
    await fetch(`${API_BASE}/chat/clear`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: conversationId }),
    });
}

export async function fetchSystemStats(): Promise<SystemStats> {
    const res = await fetch(`${API_BASE}/system/stats`);
    if (!res.ok) throw new Error('Failed to fetch stats');
    return res.json();
}

export async function healthCheck(): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE}/system/health`);
        return res.ok;
    } catch {
        return false;
    }
}
