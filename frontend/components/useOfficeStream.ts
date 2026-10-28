import { useEffect, useState } from 'react';
import { api, BASE, getToken, type Row } from '../api';

export function useOfficeStream(officeId: string) {
  const [scene, setScene] = useState<Row | null>(null);
  const [connection, setConnection] = useState<'offline' | 'rest' | 'live'>('offline');
  useEffect(() => {
    let stopped = false;
    let socket: WebSocket | undefined;
    let reconnect: ReturnType<typeof setTimeout>;
    let lastMessage = 0;
    let receiving = false;
    setScene(null);
    setConnection('offline');
    async function recover() {
      if (stopped || receiving) return;
      try {
        const value = await api(`offices/${officeId}/scene`);
        if (!stopped && !receiving) {
          setScene(value);
          setConnection('rest');
        }
      } catch {
        if (!stopped && !receiving) setConnection('offline');
      }
    }
    function connect() {
      if (stopped) return;
      socket = new WebSocket(BASE.replace('http', 'ws') + `/ws/offices/${officeId}`);
      socket.onopen = () => socket?.send(JSON.stringify({ token: getToken() }));
      socket.onmessage = (event) => {
        if (stopped) return;
        try {
          const value = JSON.parse(event.data);
          lastMessage = Date.now();
          receiving = true;
          setConnection('live');
          if (value.type !== 'heartbeat') setScene(value);
        } catch {
          socket?.close();
        }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (stopped) return;
        receiving = false;
        setConnection('offline');
        void recover();
        reconnect = setTimeout(connect, 3000);
      };
    }
    void recover();
    connect();
    const timer = setInterval(() => {
      if (receiving && Date.now() - lastMessage > 9000) socket?.close();
      void recover();
    }, 3000);
    return () => {
      stopped = true;
      clearInterval(timer);
      clearTimeout(reconnect);
      socket?.close();
    };
  }, [officeId]);
  return { scene, setScene, connection };
}
