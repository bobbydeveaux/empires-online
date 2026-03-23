// Mock axios before importing api module
jest.mock('axios', () => {
  const instance = {
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
    get: jest.fn(),
    post: jest.fn(),
  };
  return {
    __esModule: true,
    default: { create: jest.fn(() => instance) },
    _instance: instance,
  };
});

import { buildWebSocketUrl, gamesAPI } from './api';

// Access the mock instance via require (after mock is set up)
const { _instance: mockAxios } = jest.requireMock('axios');

const originalLocation = window.location;

beforeEach(() => {
  localStorage.clear();
  jest.clearAllMocks();
});

afterEach(() => {
  Object.defineProperty(window, 'location', {
    value: originalLocation,
    writable: true,
  });
});

function setLocation(protocol: string, host: string) {
  Object.defineProperty(window, 'location', {
    value: { protocol, host },
    writable: true,
  });
}

describe('buildWebSocketUrl', () => {
  it('builds ws:// URL from relative API base with token', () => {
    setLocation('http:', 'localhost:3000');
    localStorage.setItem('authToken', 'test-jwt-token');

    const url = buildWebSocketUrl(42);
    expect(url).toBe('ws://localhost:3000/ws/42?token=test-jwt-token');
  });

  it('builds wss:// URL when page is served over https', () => {
    setLocation('https:', 'example.com');
    localStorage.setItem('authToken', 'my-token');

    const url = buildWebSocketUrl(1);
    expect(url).toBe('wss://example.com/ws/1?token=my-token');
  });

  it('omits token query param when no auth token stored', () => {
    setLocation('http:', 'localhost:3000');

    const url = buildWebSocketUrl(5);
    expect(url).toBe('ws://localhost:3000/ws/5');
  });

  it('encodes special characters in token', () => {
    setLocation('http:', 'localhost:3000');
    localStorage.setItem('authToken', 'token with spaces&special=chars');

    const url = buildWebSocketUrl(1);
    expect(url).toContain('?token=token%20with%20spaces%26special%3Dchars');
  });
});

describe('gamesAPI.spectateGame', () => {
  it('calls POST /games/{gameId}/spectate and returns the response', async () => {
    const mockResponse = { data: { spectator_token: 'spec-token-123', game_id: 42 } };
    mockAxios.post.mockResolvedValue(mockResponse);

    const result = await gamesAPI.spectateGame(42);
    expect(mockAxios.post).toHaveBeenCalledWith('/games/42/spectate');
    expect(result).toEqual({ spectator_token: 'spec-token-123', game_id: 42 });
  });
});
