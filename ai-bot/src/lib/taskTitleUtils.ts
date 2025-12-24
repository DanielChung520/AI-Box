/**
 * 代碼功能說明: 任務標題工具函數
 * 創建日期: 2025-12-21
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-21
 */

/**
 * 檢測消息是否是問候語
 */
export function isGreetingMessage(text: string): boolean {
  const trimmed = text.trim().toLowerCase();
  
  // 常見的問候語模式
  const greetingPatterns = [
    /^(hi|hello|hey|你好|您好|嗨|哈囉)/i,
    /^(good\s+(morning|afternoon|evening))/i,
    /^(早上好|下午好|晚上好)/,
    /^(nice\s+to\s+meet\s+you)/i,
    /^(很高興認識你|很高興見到你)/,
    /^(how\s+are\s+you)/i,
    /^(最近好嗎|最近怎麼樣)/,
    /^(what's\s+up)/i,
    /^(最近如何)/,
    /^(thanks|thank\s+you|謝謝|感謝)/i,
  ];
  
  // 檢查是否匹配問候語模式
  for (const pattern of greetingPatterns) {
    if (pattern.test(trimmed)) {
      return true;
    }
  }
  
  // 如果消息很短（少於5個字符）且只包含問候詞，也視為問候語
  if (trimmed.length <= 5) {
    const shortGreetings = ['hi', 'hey', '你好', '您好', '嗨', '哈囉', 'thanks', '謝謝'];
    if (shortGreetings.includes(trimmed)) {
      return true;
    }
  }
  
  return false;
}

/**
 * 從消息中提取標題
 * - 如果是問候語，返回 "新任務"
 * - 否則，截取前50個字符作為標題
 */
export function extractTaskTitle(messageText: string): string {
  const trimmed = messageText.trim();
  
  if (!trimmed) {
    return '新任務';
  }
  
  // 檢測是否是問候語
  if (isGreetingMessage(trimmed)) {
    return '新任務';
  }
  
  // 截取前50個字符作為標題
  // 如果包含換行符，只取第一行
  const firstLine = trimmed.split('\n')[0].trim();
  if (firstLine.length <= 50) {
    return firstLine;
  }
  
  // 如果超過50個字符，截取前50個字符並添加省略號
  return firstLine.substring(0, 47) + '...';
}

