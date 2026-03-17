import { renderHook, act } from '@testing-library/react';
import { useGameWebSocket } from './useGameWebSocket';
import { gamesAPI } from '../services/api';

// Mock gamesAPI
jest.mock('../services/api', () => ({
  gamesAPI: {
    getGameState: jest.fn(),
  },
}));

// Mock WebSocket
class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.OPEN;
  onopen: ((event: any) => void) | null = null;
  onclose: ((event: any) => void) | null = null;
  onmessage: ((event: any) => void) | null = null;
  onerror: ((event: any) => void) | null = null;
  close = jest.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });
  send = jest.fn();

  constructor(url: string) {
    this.url = url;
    // Store reference so tests can trigger events
    mockWebSocketInstances.push(this);
  }

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.({});
  }

  simulateMessage(data: any) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateClose() {
    this.onclose?.({});
  }

  simulateError() {
    this.onerror?.({});
  }
}

let mockWebSocketInstances: MockWebSocket[] = [];

beforeEach(() => {
  mockWebSocketInstances = [];
  (global as any).WebSocket = MockWebSocket;
  localStorage.setItem('authToken', 'test-jwt-token');
  jest.useFakeTimers();
  (gamesAPI.getGameState as jest.Mock).mockResolvedValue({
    game: { id: 1, phase: 'waiting', rounds: 5, rounds_remaining: 5 },
    players: [],
    leaderboard: [],
  });
});

afterEach(() => {
  jest.useRealTimers();
  localStorage.clear();
  jest.restoreAllMocks();
});

describe('useGameWebSocket', () => {
  it('connects to WebSocket on mount when gameId is provided', () => {
    renderHook(() => useGameWebSocket(1));

    expect(mockWebSocketInstances).toHaveLength(1);
    expect(mockWebSocketInstances[0].url).toContain('/ws/1?token=test-jwt-token');
  });

  it('does not connect when gameId is null', () => {
    renderHook(() => useGameWebSocket(null));

    expect(mockWebSocketInstances).toHaveLength(0);
  });

  it('does not connect when no auth token exists', () => {
    localStorage.clear();
    const { result } = renderHook(() => useGameWebSocket(1));

    expect(mockWebSocketInstances).toHaveLength(0);
    expect(result.current.connectionStatus).toBe('disconnected');
  });

  it('sets status to connected on open and fetches full state', async () => {
    const { result } = renderHook(() => useGameWebSocket(1));

    expect(result.current.connectionStatus).toBe('connecting');

    await act(async () => {
      mockWebSocketInstances[0].simulateOpen();
    });

    expect(result.current.connectionStatus).toBe('connected');
    expect(gamesAPI.getGameState).toHaveBeenCalledWith(1);
  });

  it('updates gameState from REST response on connect', async () => {
    const mockState = {
      game: { id: 1, phase: 'development', rounds: 5, rounds_remaining: 4 },
      players: [],
      leaderboard: [],
    };
    (gamesAPI.getGameState as jest.Mock).mockResolvedValue(mockState);

    const { result } = renderHook(() => useGameWebSocket(1));

    await act(async () => {
      mockWebSocketInstances[0].simulateOpen();
    });

    expect(result.current.gameState).toEqual(mockState);
  });

  it('handles game_state_update messages', async () => {
    const { result } = renderHook(() => useGameWebSocket(1));

    await act(async () => {
      mockWebSocketInstances[0].simulateOpen();
    });

    const newState = {
      game: { id: 1, phase: 'actions', rounds: 5, rounds_remaining: 3 },
      players: [],
      leaderboard: [],
    };

    act(() => {
      mockWebSocketInstances[0].simulateMessage({
        type: 'game_state_update',
        game_id: 1,
        state: newState,
      });
    });

    expect(result.current.gameState).toEqual(newState);
  });

  it('fetches full state on player_joined/player_left messages', async () => {
    const { result } = renderHook(() => useGameWebSocket(1));

    await act(async () => {
      mockWebSocketInstances[0].simulateOpen();
    });

    (gamesAPI.getGameState as jest.Mock).mockClear();

    await act(async () => {
      mockWebSocketInstances[0].simulateMessage({
        type: 'player_joined',
        game_id: 1,
        player: { id: 2, username: 'player2' },
      });
    });

    expect(gamesAPI.getGameState).toHaveBeenCalledWith(1);

    (gamesAPI.getGameState as jest.Mock).mockClear();

    await act(async () => {
      mockWebSocketInstances[0].simulateMessage({
        type: 'player_left',
        game_id: 1,
        player: { id: 2, username: 'player2' },
      });
    });

    expect(gamesAPI.getGameState).toHaveBeenCalledWith(1);
  });

  it('exposes lastMessage for chat and error messages', async () => {
    const { result } = renderHook(() => useGameWebSocket(1));

    await act(async () => {
      mockWebSocketInstances[0].simulateOpen();
    });

    act(() => {
      mockWebSocketInstances[0].simulateMessage({
        type: 'chat',
        game_id: 1,
        player: { id: 2, username: 'player2' },
        message: 'Hello!',
      });
    });

    expect(result.current.lastMessage).toEqual({
      type: 'chat',
      game_id: 1,
      player: { id: 2, username: 'player2' },
      message: 'Hello!',
    });
  });

  it('reconnects with exponential backoff on unintentional close', async () => {
    const { result } = renderHook(() => useGameWebSocket(1));

    await act(async () => {
      mockWebSocketInstances[0].simulateOpen();
    });

    // Simulate unintentional close
    act(() => {
      mockWebSocketInstances[0].simulateClose();
    });

    expect(result.current.connectionStatus).toBe('reconnecting');

    // First reconnect after 1s
    act(() => { jest.advanceTimersByTime(1000); });
    expect(mockWebSocketInstances).toHaveLength(2);

    // Simulate second close
    act(() => {
      mockWebSocketInstances[1].simulateClose();
    });

    // Second reconnect after 2s
    act(() => { jest.advanceTimersByTime(1000); });
    expect(mockWebSocketInstances).toHaveLength(2); // Not yet
    act(() => { jest.advanceTimersByTime(1000); });
    expect(mockWebSocketInstances).toHaveLength(3);

    // Third close — should wait 4s
    act(() => {
      mockWebSocketInstances[2].simulateClose();
    });

    act(() => { jest.advanceTimersByTime(3000); });
    expect(mockWebSocketInstances).toHaveLength(3); // Not yet
    act(() => { jest.advanceTimersByTime(1000); });
    expect(mockWebSocketInstances).toHaveLength(4);
  });

  it('caps reconnect delay at 30 seconds', async () => {
    const { result } = renderHook(() => useGameWebSocket(1));

    await act(async () => {
      mockWebSocketInstances[0].simulateOpen();
    });

    // Simulate many disconnects to exceed 30s cap
    // delays: 1s, 2s, 4s, 8s, 16s, 32s -> capped at 30s
    for (let i = 0; i < 5; i++) {
      act(() => { mockWebSocketInstances[mockWebSocketInstances.length - 1].simulateClose(); });
      act(() => { jest.advanceTimersByTime(30000); });
    }

    // After 5 disconnects, delay should be capped at 30s
    act(() => { mockWebSocketInstances[mockWebSocketInstances.length - 1].simulateClose(); });

    // Should not reconnect at 29s
    act(() => { jest.advanceTimersByTime(29000); });
    const countBefore = mockWebSocketInstances.length;

    // Should reconnect at 30s
    act(() => { jest.advanceTimersByTime(1000); });
    expect(mockWebSocketInstances.length).toBe(countBefore + 1);
  });

  it('manual reconnect resets backoff and reconnects immediately', async () => {
    const { result } = renderHook(() => useGameWebSocket(1));

    await act(async () => {
      mockWebSocketInstances[0].simulateOpen();
    });

    act(() => {
      result.current.reconnect();
    });

    // After setTimeout(0) tick
    act(() => { jest.advanceTimersByTime(0); });

    // A new WebSocket should be created
    expect(mockWebSocketInstances.length).toBeGreaterThanOrEqual(2);
  });

  it('disconnects on unmount', async () => {
    const { unmount } = renderHook(() => useGameWebSocket(1));

    await act(async () => {
      mockWebSocketInstances[0].simulateOpen();
    });

    unmount();

    expect(mockWebSocketInstances[0].close).toHaveBeenCalled();
  });

  it('sends periodic pings', async () => {
    renderHook(() => useGameWebSocket(1));

    await act(async () => {
      mockWebSocketInstances[0].simulateOpen();
    });

    act(() => { jest.advanceTimersByTime(30000); });

    expect(mockWebSocketInstances[0].send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'ping' })
    );
  });
});
