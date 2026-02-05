import { Brain } from 'lucide-react';
import { useAIStatusStore } from '../../stores/aiStatusStore';
import './BrainIcon.css';

export default function BrainIcon() {
  const { currentStatus, isConnected, toggleWindow, isWindowOpen } = useAIStatusStore();

  const getStatusClass = () => {
    switch (currentStatus) {
      case 'processing':
        return 'status-processing';
      case 'completed':
        return 'status-completed';
      case 'error':
        return 'status-error';
      default:
        return 'status-idle';
    }
  };

  return (
    <div className={`brain-icon-container ${getStatusClass()}`} onClick={toggleWindow}>
      <Brain
        size={24}
        className={`brain-icon ${isWindowOpen ? 'active' : ''}`}
      />
      <span className="status-dot" />
    </div>
  );
}
