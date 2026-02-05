import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, AlertCircle, Clock, Brain, Activity, Loader } from 'lucide-react';
import { useAIStatusStore } from '../../stores/aiStatusStore';
import { useMemo } from 'react';
import './AIStatusWindow.css';

const getStatusConfig = (status: string) => {
  switch (status) {
    case 'processing':
      return { icon: Loader, color: '#52c41a', label: '處理中', iconClass: 'processing' };
    case 'completed':
      return { icon: CheckCircle, color: '#1890ff', label: '完成', iconClass: 'completed' };
    case 'error':
      return { icon: AlertCircle, color: '#ff4d4f', label: '錯誤', iconClass: 'error' };
    default:
      return { icon: Clock, color: '#999', label: '等待', iconClass: 'idle' };
  }
};

const formatDuration = (ms: number): string => {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  } else if (ms < 60000) {
    return `${(ms / 1000).toFixed(1)}s`;
  } else {
    return `${(ms / 60000).toFixed(1)}m`;
  }
};

// 過濾 heartbeat 事件
const filterNonHeartbeatEvents = (events: any[]) => {
  return events.filter(event => {
    if (event.step === 'heartbeat' || event.step === 'Heartbeat') {
      return false;
    }
    if (event.message?.includes('heartbeat')) {
      return false;
    }
    return true;
  });
};

// 解析多行消息為陣列
const parseMessageLines = (message: string) => {
  if (!message) return [];
  return message.split('\n').filter(line => line.trim());
};

export default function AIStatusWindow() {
  const { isWindowOpen, closeWindow, events, isConnected, requestId } = useAIStatusStore();

  // 過濾掉 heartbeat 事件
  const filteredEvents = useMemo(() => filterNonHeartbeatEvents(events), [events]);

  // 計算性能統計
  const performanceStats = useMemo(() => {
    if (filteredEvents.length === 0) {
      return null;
    }

    const startTime = new Date(filteredEvents[0].timestamp).getTime();
    const endTime = new Date(filteredEvents[filteredEvents.length - 1].timestamp).getTime();
    const totalDuration = endTime - startTime;

    const steps = filteredEvents.map((event, index) => {
      const timestamp = new Date(event.timestamp).getTime();
      const prevTimestamp = index > 0 ? new Date(filteredEvents[index - 1].timestamp).getTime() : timestamp;
      const duration = timestamp - prevTimestamp;

      return {
        ...event,
        duration,
        durationStr: formatDuration(duration),
      };
    });

    // 找出最耗時的步驟
    const slowestStep = [...steps].sort((a, b) => b.duration - a.duration)[0];

    return {
      totalDuration,
      totalDurationStr: formatDuration(totalDuration),
      steps,
      slowestStep,
      eventCount: filteredEvents.length,
    };
  }, [filteredEvents]);

  // 獲取當前進度
  const currentProgress = useMemo(() => {
    const lastProcessing = [...filteredEvents].reverse().find((e) => e.status === 'processing');
    return lastProcessing?.progress ?? filteredEvents[filteredEvents.length - 1]?.progress ?? 0;
  }, [filteredEvents]);

  return (
    <AnimatePresence>
      {isWindowOpen && (
        <motion.div
          className="ai-status-window"
          initial={{ opacity: 0, y: 10, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.95 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
        >
          <div className="ai-status-header">
            <div className="ai-status-title">
              <Brain size={18} />
              <span>AI 執行報告</span>
            </div>
            <div className="ai-status-header-actions">
              <button className="close-button" onClick={closeWindow}>
                <X size={18} />
              </button>
            </div>
          </div>

          {/* 全局進度條 */}
          <div className="global-progress-container">
            <div className="global-progress-header">
              <span className="progress-label">執行進度</span>
              <span className="progress-value">{Math.round(currentProgress * 100)}%</span>
            </div>
            <div className="global-progress-bar">
              <motion.div
                className="global-progress-fill"
                initial={{ width: 0 }}
                animate={{ width: `${currentProgress * 100}%` }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              />
            </div>
          </div>

          {/* 性能統計 */}
          {performanceStats && performanceStats.eventCount > 0 && (
            <div className="performance-stats">
              <div className="stat-item">
                <Activity size={14} />
                <span className="stat-label">總耗時</span>
                <span className="stat-value">{performanceStats.totalDurationStr}</span>
              </div>
              <div className="stat-item">
                <Clock size={14} />
                <span className="stat-label">步驟數</span>
                <span className="stat-value">{performanceStats.eventCount}</span>
              </div>
              {performanceStats.slowestStep && performanceStats.slowestStep.duration > 100 && (
                <div className="stat-item slowest">
                  <span className="stat-label">瓶頸</span>
                  <span className="stat-value">{performanceStats.slowestStep.step}</span>
                  <span className="stat-duration">({performanceStats.slowestStep.durationStr})</span>
                </div>
              )}
            </div>
          )}

          <div className="ai-status-content">
            {filteredEvents.length === 0 ? (
              <div className="ai-status-empty">
                <Brain size={32} className="empty-icon" />
                <p>AI 尚未開始執行</p>
                <p className="empty-hint">當您發送消息給 AI 時，這裡會顯示執行過程</p>
              </div>
            ) : (
              <div className="ai-status-list">
                {performanceStats?.steps.map((step, index) => {
                  const config = getStatusConfig(step.status);
                  const IconComponent = config.icon;
                  const lines = parseMessageLines(step.message);

                  return (
                    <motion.div
                      key={`${step.request_id}-${index}`}
                      className={`ai-status-item ${step.status}`}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.2, delay: index * 0.05 }}
                    >
                      <div className="status-item-header">
                        <IconComponent
                          size={16}
                          className={`status-icon ${config.iconClass}`}
                          style={{ animation: step.status === 'processing' ? 'spin 1s linear infinite' : undefined }}
                        />
                        <span className="status-label" style={{ color: config.color }}>
                          {config.label}
                        </span>
                        <span className="step-name">{step.step}</span>
                      </div>

                      {lines.length > 0 && (
                        <div className="status-item-content">
                          {lines.map((line, i) => (
                            <span key={i} className="message-line">
                              {line}
                            </span>
                          ))}
                        </div>
                      )}

                      <div className="status-item-footer">
                        <span className="timestamp">
                          {new Date(step.timestamp).toLocaleTimeString('zh-TW', { hour12: false })}
                        </span>
                        {step.duration > 50 && (
                          <span className={`duration ${step.duration > 500 ? 'slow' : ''}`}>
                            +{step.durationStr}
                          </span>
                        )}
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="ai-status-footer">
            <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
              <span className="status-dot" />
              <span>{isConnected ? '已連線' : '未連線'}</span>
            </div>
            {requestId && (
              <div className="request-id">
                <span className="request-id-label">請求:</span>
                <span className="request-id-value">{requestId.slice(0, 8)}</span>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
