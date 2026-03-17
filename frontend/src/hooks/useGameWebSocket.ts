import { useState, useEffect, useRef, useCallback } from 'react';
import { GameState, ConnectionStatus, WsServerMessage } from '../types';
import { gamesAPI } from '../services/api';

const INITIAL_RECONNECT_DELAY = 1000; // 1 second
const MAX_RECONNECT_DELAY = 30000; // 30 seconds
const PING_INTERVAL = 30000; // 30 seconds

/**
 * Build the WebSocket URL for a given game ID.
 * Uses the current page origin, swapping http(s) for ws(s).
 */
function buildWsUrl(gameId: number, token: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/ws/${gameId}?token=${encodeURIComponent(token)}`;
}

interface UseGameWebSocketReturn {
  gameState: GameState | null;
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
  lastMessage: WsServerMessage | null;
}

export function useGameWebSocket(gameId: number | null): UseGameWebSocketReturn {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WsServerMessage | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);
  const intentionalCloseRef = useRef(false);

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

  const closeSocket = useCallback(() => {
    intentionalCloseRef.current = true;
    clearTimers();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, [clearTimers]);

  /** Fetch full game state via REST to ensure sync after (re)connect. */
  const fetchFullState = useCallback(async (id: number) => {
    try {
      const state = await gamesAPI.getGameState(id);
      if (mountedRef.current) {
        setGameState(state);
      }
    } catch {
      // REST fetch failed — state will update on next WS message or retry
    }
  }, []);

  const connect = useCallback(() => {
    if (!gameId) return;

    const token = localStorage.getItem('authToken');
    if (!token) {
      setConnectionStatus('disconnected');
      return;
    }

    // Clean up any existing connection
    if (wsRef.current) {
      intentionalCloseRef.current = true;
      wsRef.current.close();
      wsRef.current = null;
    }

    intentionalCloseRef.current = false;
    setConnectionStatus('connecting');

    const url = buildWsUrl(gameId, token);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setConnectionStatus('connected');
      reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;

      // Fetch full state on connect to ensure sync
      fetchFullState(gameId);

      // Start ping keepalive
      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = (event: MessageEvent) => {
      if (!mountedRef.current) return;

      let message: WsServerMessage;
      try {
        message = JSON.parse(event.data);
      } catch {
        return; // Ignore unparseable messages
      }

      setLastMessage(message);

      switch (message.type) {
        case 'game_state_update':
          setGameState(message.state);
          break;

        case 'player_joined':
        case 'player_left':
          // A player change occurred — refresh full state to stay in sync
          fetchFullState(gameId);
          break;

        case 'pong':
          // Keepalive response — no action needed
          break;

        case 'chat':
        case 'error':
          // Exposed via lastMessage for consumers to handle
          break;
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;

      // Clean up ping timer
      if (pingTimerRef.current) {
        clearInterval(pingTimerRef.current);
        pingTimerRef.current = null;
      }

      if (intentionalCloseRef.current) {
        setConnectionStatus('disconnected');
        return;
      }

      // Schedule reconnect with exponential backoff
      setConnectionStatus('reconnecting');
      const delay = reconnectDelayRef.current;
      reconnectTimerRef.current = setTimeout(() => {
        if (mountedRef.current) {
          connect();
        }
      }, delay);

      // Increase delay for next attempt (exponential backoff, capped at max)
      reconnectDelayRef.current = Math.min(delay * 2, MAX_RECONNECT_DELAY);
    };

    ws.onerror = () => {
      // The onclose handler will fire after onerror, handling reconnection
    };
  }, [gameId, fetchFullState, clearTimers]);

  /** Manual reconnect — resets backoff delay and reconnects immediately. */
  const reconnect = useCallback(() => {
    reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
    closeSocket();
    // Small delay to let the close propagate
    setTimeout(() => {
      if (mountedRef.current) {
        intentionalCloseRef.current = false;
        connect();
      }
    }, 0);
  }, [closeSocket, connect]);

  // Connect on mount / when gameId changes, disconnect on unmount
  useEffect(() => {
    mountedRef.current = true;

    if (gameId) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      closeSocket();
    };
  }, [gameId, connect, closeSocket]);

  return { gameState, connectionStatus, reconnect, lastMessage };
}
