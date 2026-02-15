export interface HypothesisResult {
    id: string;
    name: string;
    description: string;
    score: number;
}

export interface QueryResponse {
    query: string;
    insight: string;
    sql: string | null;
    execution_time_ms: number;
    rows_returned: number;
    data: Record<string, unknown>[];
    signals: string[];
    hypotheses: HypothesisResult[];
    error: string | null;
}

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    response?: QueryResponse;
    isLoading?: boolean;
}

export interface SystemStats {
    database: {
        row_count: number;
        column_count: number;
        columns: string[];
    };
    hypotheses_loaded: number;
    history_length: number;
    executor: {
        time_ms: number;
        rows_returned: number;
        cache_size: number;
    };
}
