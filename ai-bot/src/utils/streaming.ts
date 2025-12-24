/**
 * 代碼功能說明: 流式傳輸工具 - 支持 SSE 流式數據接收和解析
 * 創建日期: 2025-12-20 12:30:07 (UTC+8)
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-20 12:30:07 (UTC+8)
 */

/**
 * 流式傳輸消息類型
 */
export type StreamingMessageType = 'patch_start' | 'patch_chunk' | 'patch_end' | 'error';

/**
 * 流式傳輸消息
 */
export interface StreamingMessage {
  type: StreamingMessageType;
  data: Record<string, unknown>;
}

/**
 * 流式狀態機狀態
 */
export type StreamingState = 'idle' | 'connecting' | 'streaming' | 'completed' | 'error';

/**
 * 流式傳輸事件監聽器
 */
export interface StreamingEventListeners {
  onMessage?: (message: StreamingMessage) => void;
  onStateChange?: (state: StreamingState) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

/**
 * SSE 流式傳輸客戶端
 */
export class SSEStreamingClient {
  private eventSource: EventSource | null = null;
  private state: StreamingState = 'idle';
  private listeners: StreamingEventListeners = {};
  private buffer: string = '';

  constructor(
    private url: string,
    listeners: StreamingEventListeners = {}
  ) {
    this.listeners = listeners;
  }

  /**
   * 連接到 SSE 端點
   */
  connect(): void {
    if (this.state === 'connecting' || this.state === 'streaming') {
      console.warn('Already connected or connecting');
      return;
    }

    this.setState('connecting');

    try {
      this.eventSource = new EventSource(this.url);

      this.eventSource.onopen = () => {
        this.setState('streaming');
      };

      this.eventSource.onmessage = (event) => {
        this.handleMessage(event.data);
      };

      this.eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        this.setState('error');
        this.listeners.onError?.(new Error('SSE connection error'));
      };
    } catch (error) {
      console.error('Failed to create EventSource:', error);
      this.setState('error');
      this.listeners.onError?.(error as Error);
    }
  }

  /**
   * 處理接收到的消息
   */
  private handleMessage(data: string): void {
    try {
      // SSE 格式：data: {...}
      if (data.startsWith('data: ')) {
        const jsonStr = data.slice(6); // 移除 "data: " 前綴
        const message: StreamingMessage = JSON.parse(jsonStr);

        // 處理不同類型的消息
        switch (message.type) {
          case 'patch_start':
            this.buffer = '';
            this.listeners.onMessage?.(message);
            break;

          case 'patch_chunk':
            // 累積數據塊
            if (message.data.chunk && typeof message.data.chunk === 'string') {
              this.buffer += message.data.chunk;
            }
            this.listeners.onMessage?.(message);
            break;

          case 'patch_end':
            // 發送完整數據
            if (this.buffer) {
              try {
                const completeData = JSON.parse(this.buffer);
                this.listeners.onMessage?.({
                  type: 'patch_end',
                  data: { ...message.data, complete: completeData },
                });
              } catch (parseError) {
                console.error('Failed to parse complete data:', parseError);
              }
            } else {
              this.listeners.onMessage?.(message);
            }
            this.setState('completed');
            this.listeners.onComplete?.();
            break;

          case 'error':
            this.setState('error');
            this.listeners.onError?.(new Error(message.data.error as string || 'Unknown error'));
            break;

          default:
            console.warn('Unknown message type:', message.type);
        }
      }
    } catch (error) {
      console.error('Failed to parse message:', error);
      this.listeners.onError?.(error as Error);
    }
  }

  /**
   * 更新狀態
   */
  private setState(state: StreamingState): void {
    if (this.state !== state) {
      this.state = state;
      this.listeners.onStateChange?.(state);
    }
  }

  /**
   * 斷開連接
   */
  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.setState('idle');
    this.buffer = '';
  }

  /**
   * 獲取當前狀態
   */
  getState(): StreamingState {
    return this.state;
  }

  /**
   * 檢查是否已連接
   */
  isConnected(): boolean {
    return this.state === 'streaming' || this.state === 'connecting';
  }
}

/**
 * 流式狀態機
 */
export class StreamingStateMachine {
  private state: StreamingState = 'idle';
  private patches: Array<{ search_block: string; replace_block: string }> = [];
  private currentPatch: { search_block: string; replace_block: string } | null = null;

  /**
   * 處理流式消息
   */
  handleMessage(message: StreamingMessage): void {
    switch (message.type) {
      case 'patch_start':
        this.state = 'streaming';
        this.patches = [];
        this.currentPatch = null;
        break;

      case 'patch_chunk':
        if (this.state === 'streaming') {
          // 解析 chunk 並更新當前 patch
          const chunk = message.data.chunk as string;
          this.processChunk(chunk);
        }
        break;

      case 'patch_end':
        if (this.currentPatch) {
          this.patches.push(this.currentPatch);
          this.currentPatch = null;
        }
        this.state = 'completed';
        break;

      case 'error':
        this.state = 'error';
        break;
    }
  }

  /**
   * 處理數據塊
   */
  private processChunk(chunk: string): void {
    // 簡單實現：累積 chunk 直到可以解析完整的 JSON
    // 實際應該使用更複雜的狀態機來解析流式 JSON
    try {
      // 嘗試解析累積的數據
      const buffer = this.getBuffer();
      const parsed = JSON.parse(buffer + chunk);
      if (parsed.patches && Array.isArray(parsed.patches)) {
        this.patches = parsed.patches;
        this.currentPatch = null;
      }
    } catch {
      // 數據不完整，繼續累積
      this.appendToBuffer(chunk);
    }
  }

  private buffer: string = '';

  private getBuffer(): string {
    return this.buffer;
  }

  private appendToBuffer(chunk: string): void {
    this.buffer += chunk;
  }

  /**
   * 獲取當前狀態
   */
  getState(): StreamingState {
    return this.state;
  }

  /**
   * 獲取解析後的 patches
   */
  getPatches(): Array<{ search_block: string; replace_block: string }> {
    return this.patches;
  }

  /**
   * 重置狀態機
   */
  reset(): void {
    this.state = 'idle';
    this.patches = [];
    this.currentPatch = null;
    this.buffer = '';
  }
}

/**
 * 連接到編輯流式端點
 */
export function connectEditingStream(
  sessionId: string,
  requestId?: string,
  listeners: StreamingEventListeners = {}
): SSEStreamingClient {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const url = `${baseUrl}/api/v1/streaming/editing/${sessionId}/stream${requestId ? `?request_id=${requestId}` : ''}`;

  const client = new SSEStreamingClient(url, listeners);
  client.connect();

  return client;
}
