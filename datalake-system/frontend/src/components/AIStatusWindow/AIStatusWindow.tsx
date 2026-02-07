import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, AlertCircle, Clock, Brain } from 'lucide-react';
import { useAIStatusStore } from '../../stores/aiStatusStore';
import './AIStatusWindow.css';

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'processing':
      return <Clock size={16} className="status-icon processing" />;
    case 'completed':
      return <CheckCircle size={16} className="status-icon completed" />;
    case 'error':
      return <AlertCircle size={16} className="status-icon error" />;
    default:
      return <Brain size={16} className="status-icon idle" />;
  }
};

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'processing':
      return '處理中';
    case 'completed':
      return '完成';
    case 'error':
      return '錯誤';
    default:
      return '閒置';
  }
};

const isHeartbeat = (step: string) => step === 'heartbeat';

export default function AIStatusWindow() {
  const { isWindowOpen, closeWindow, events, currentStatus, isConnected } = useAIStatusStore();

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
              <span>AI 執行狀態</span>
            </div>
            <button className="close-button" onClick={closeWindow}>
              <X size={18} />
            </button>
          </div>

          <div className="ai-status-content">
            {events.length === 0 ? (
              <div className="ai-status-empty">
                <Brain size={32} className="empty-icon" />
                <p>AI 尚未開始執行</p>
                <p className="empty-hint">當 AI 處理任務時，這裡會顯示執行狀態</p>
              </div>
            ) : (
              <div className="ai-status-list">
                {events.map((event, index) => (
                  <motion.div
                    key={`${event.request_id}-${index}`}
                    className={`ai-status-item ${isHeartbeat(event.step) ? 'heartbeat-item' : ''}`}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.15 }}
                  >
                    <div className="status-item-header">
                      {isHeartbeat(event.step) ? (
                        <Clock size={16} className="status-icon processing" style={{ animation: 'pulse 1.5s infinite' }} />
                      ) : (
                        getStatusIcon(event.status)
                      )}
                      <span className="status-label">{isHeartbeat(event.step) ? '執行中' : getStatusLabel(event.status)}</span>
                      {event.progress > 0 && !isHeartbeat(event.step) && (
                        <div className="progress-bar">
                          <motion.div
                            className="progress-fill"
                            initial={{ width: 0 }}
                            animate={{ width: `${event.progress * 100}%` }}
                            transition={{ duration: 0.2 }}
                          />
                        </div>
                      )}
                    </div>
                    <div className="status-item-content">
                      <span className="step-name">{event.step}</span>
                      <span className="message">{event.message}</span>
                    </div>
                    <span className="timestamp">
                      {new Date(event.timestamp).toLocaleTimeString('zh-TW')}
                    </span>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          <div className="ai-status-footer">
            <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
              <span className="status-dot" />
              <span>{isConnected ? '已連線' : '未連線'}</span>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
