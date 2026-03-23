import { useEffect, useRef, useCallback, useState } from 'react';
import { GameState, WsServerMessage, WsConnectionStatus } from '../types';
import { gamesAPI, getWebSocketUrl } from '../services/api';

const INITIAL_RECONNECT_DELAY = 1000;
const MAX_RECONNECT_DELAY = 30000;
const PING_INTERVAL = 25000;

interface UseGameWebSocketOptions {
  /** Game ID to connect to. Pass null/undefined to skip connection. */
  gameId: number | null | undefined;
  /** JWT auth token. Connection won't open without it. */
  token: string | null;
  /** Called when a WebSocket message is received. */
  onMessage?: (message: WsServerMessage) => void;
  /** When true, connects in read-only spectator mode (no outbound action messages). */
  isSpectator?: boolean;
}

interface UseGameWebSocketReturn {
  /** Current game state (fetched via REST, kept in sync by WS events). */
  gameState: GameState | null;
  /** WebSocket connection status. */
  connectionStatus: WsConnectionStatus;
  /** Manually trigger a reconnect. */
  reconnect: () => void;
  /** Manually refresh game state via REST. */
  refreshGameState: () => Promise<void>;
}

export function useGameWebSocket({
  gameId,
  token,
  onMessage,
}: UseGameWebSocketOptions): UseGameWebSocketReturn {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<WsConnectionStatus>('disconnected');

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  // Fetch full game state via REST
  const fetchGameState = useCallback(async () => {
    if (!gameId) return;
    try {
      const state = await gamesAPI.getGameState(gameId);
      if (mountedRef.current) {
        setGameState(state);
      }
    } catch {
      // Silently fail — state will be retried on next event or reconnect
    }
  }, [gameId]);

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current);
      pingTimerRef.current = null;
    }
  }, []);

  const closeConnection = useCallback(() => {
    clearTimers();
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close();
      }
      wsRef.current = null;
    }
  }, [clearTimers]);

  const scheduleReconnect = useCallback(() => {
    if (!mountedRef.current) return;
    setConnectionStatus('reconnecting');
    const delay = reconnectDelayRef.current;
    reconnectTimerRef.current = setTimeout(() => {
      if (mountedRef.current) {
        reconnectDelayRef.current = Math.min(delay * 2, MAX_RECONNECT_DELAY);
        connect(); // eslint-disable-line @typescript-eslint/no-use-before-define
      }
    }, delay);
  }, []); // connect is defined below, but stable via ref pattern

  const connect = useCallback(() => {
    if (!gameId || !token || !mountedRef.current) return;

    closeConnection();
    setConnectionStatus('connecting');

    const url = getWebSocketUrl(gameId, token);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setConnectionStatus('connected');
      reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;

      // Fetch full state on connect/reconnect to ensure sync
      fetchGameState();

      // Start ping keepalive
      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = (event: MessageEvent) => {
      if (!mountedRef.current) return;
      try {
        const message: WsServerMessage = JSON.parse(event.data);

        // Forward to callback
        onMessageRef.current?.(message);

        // Handle state-affecting messages
        switch (message.type) {
          case 'game_state_update':
            if (message.game_state) {
              setGameState(message.game_state);
            } else {
              fetchGameState();
            }
            break;
          case 'player_joined':
          case 'player_left':
          case 'round_changed':
            // Re-fetch full state from REST for consistency
            fetchGameState();
            break;
          // pong, chat, error — no state refresh needed
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = (event: CloseEvent) => {
      clearTimers();
      if (!mountedRef.current) return;
      // 1008 = policy violation (auth failure) — don't reconnect
      if (event.code === 1008) {
        setConnectionStatus('disconnected');
        return;
      }
      scheduleReconnect();
    };

    ws.onerror = () => {
      // onclose will fire after onerror, so reconnect is handled there
    };
  }, [gameId, token, closeConnection, fetchGameState, clearTimers, scheduleReconnect]);

  // Manual reconnect
  const reconnect = useCallback(() => {
    reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
    connect();
  }, [connect]);

  // Connect on mount / when gameId or token changes
  useEffect(() => {
    mountedRef.current = true;
    if (gameId && token) {
      connect();
    }
    return () => {
      mountedRef.current = false;
      closeConnection();
    };
  }, [gameId, token, connect, closeConnection]);

  return {
    gameState,
    connectionStatus,
    reconnect,
    refreshGameState: fetchGameState,
  };
}
