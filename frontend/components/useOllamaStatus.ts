import { useEffect, useState } from 'react';
import { api, type Row } from '../api';

export function useOllamaStatus() {
  const [status, setStatus] = useState<Row | null>(null);
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    async function check() {
      try {
        const value = await api('ollama/status');
        if (!stopped) setStatus(value);
      } catch {
        if (!stopped) setStatus(null);
      }
      if (!stopped) timer = setTimeout(check, 30000);
    }
    void check();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, []);
  return status;
}
