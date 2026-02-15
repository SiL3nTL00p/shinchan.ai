import React from 'react';
import type { QueryResponse } from '../types';

interface Props {
    response: QueryResponse;
}

export default function MessageStats({ response }: Props) {
    return (
        <div className="flex flex-wrap gap-3 mt-2 text-[11px] text-white/35">
            {response.execution_time_ms > 0 && (
                <span>{response.execution_time_ms.toFixed(0)}ms</span>
            )}
            {response.rows_returned > 0 && (
                <span>{response.rows_returned.toLocaleString()} rows</span>
            )}
            {response.signals.length > 0 && (
                <span>{response.signals.length} signals</span>
            )}
            {response.hypotheses.length > 0 && (
                <span>
                    Top: {response.hypotheses[0].name} ({(response.hypotheses[0].score * 100).toFixed(0)}%)
                </span>
            )}
        </div>
    );
}
