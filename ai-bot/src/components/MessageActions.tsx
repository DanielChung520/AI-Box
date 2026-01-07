// 代碼功能說明：消息操作按鈕組件，包含點讚、倒讚、複製等功能
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2026-01-06

import { useState } from 'react';
import { ThumbsUp, ThumbsDown, Copy } from 'lucide-react';
import { useLanguage } from '../contexts/languageContext';

interface MessageActionsProps {
  messageId?: string;
  messageContent?: string;
  onLike?: () => void;
  onDislike?: () => void;
  onCopy?: () => void;
}

export default function MessageActions({
  messageId: _messageId,
  messageContent = '',
  onLike,
  onDislike,
  onCopy
}: MessageActionsProps) {
  const [liked, setLiked] = useState(false);
  const [disliked, setDisliked] = useState(false);
  const [copied, setCopied] = useState(false);
  const { t } = useLanguage();

  const handleLike = () => {
    // TODO: 實現點讚功能
    setLiked(!liked);
    setDisliked(false);
    if (onLike) {
      onLike();
    }
  };

  const handleDislike = () => {
    // TODO: 實現倒讚功能
    setDisliked(!disliked);
    setLiked(false);
    if (onDislike) {
      onDislike();
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(messageContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      if (onCopy) {
        onCopy();
      }
    } catch (err) {
      console.error('複製失敗:', err);
      // 降級方案：使用傳統方法
      const textArea = document.createElement('textarea');
      textArea.value = messageContent;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        if (onCopy) {
          onCopy();
        }
      } catch (fallbackErr) {
        console.error('降級複製方法也失敗:', fallbackErr);
      }
      document.body.removeChild(textArea);
    }
  };

  return (
    <div className="flex items-center gap-2 mt-2 pt-2 border-t border-primary/30">
      <button
        onClick={handleLike}
        className={`flex items-center gap-1 px-2 py-1 text-[9.6px] rounded transition-colors ${
          liked
            ? 'bg-blue-600/20 text-blue-400 hover:bg-blue-600/30'
            : 'text-tertiary hover:text-primary hover:bg-tertiary'
        }`}
        title={t('messageActions.like') || '點讚'}
        aria-label={t('messageActions.like') || '點讚'}
      >
        <ThumbsUp className="w-3.5 h-3.5" />
        <span>{t('messageActions.like') || '點讚'}</span>
      </button>

      <button
        onClick={handleDislike}
        className={`flex items-center gap-1 px-2 py-1 text-[9.6px] rounded transition-colors ${
          disliked
            ? 'bg-red-600/20 text-red-400 hover:bg-red-600/30'
            : 'text-tertiary hover:text-primary hover:bg-tertiary'
        }`}
        title={t('messageActions.dislike') || '倒讚'}
        aria-label={t('messageActions.dislike') || '倒讚'}
      >
        <ThumbsDown className="w-3.5 h-3.5" />
        <span>{t('messageActions.dislike') || '倒讚'}</span>
      </button>

      <button
        onClick={handleCopy}
        className={`flex items-center gap-1 px-2 py-1 text-[9.6px] rounded transition-colors ${
          copied
            ? 'bg-green-600/20 text-green-400'
            : 'text-tertiary hover:text-primary hover:bg-tertiary'
        }`}
        title={copied ? (t('messageActions.copied') || '已複製') : (t('messageActions.copy') || '複製')}
        aria-label={copied ? (t('messageActions.copied') || '已複製') : (t('messageActions.copy') || '複製')}
      >
        <Copy className="w-3.5 h-3.5" />
        <span>{copied ? (t('messageActions.copied') || '已複製') : (t('messageActions.copy') || '複製')}</span>
      </button>
    </div>
  );
}
