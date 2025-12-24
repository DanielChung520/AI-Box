// 代碼功能說明: Diff 工具函數（生成 unified diff）
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

/**
 * 生成 unified diff 格式的差異文本
 * @param original - 原始內容
 * @param modified - 修改後的內容
 * @returns unified diff 格式的字符串
 */
export function generateUnifiedDiff(original: string, modified: string): string {
  const originalLines = original.split('\n');
  const modifiedLines = modified.split('\n');
  
  // 使用簡單的算法生成 diff
  // 這裡使用基本的行對比算法
  const diff: string[] = [];
  diff.push('--- original');
  diff.push('+++ modified');
  
  let i = 0;
  let j = 0;
  
  while (i < originalLines.length || j < modifiedLines.length) {
    if (i >= originalLines.length) {
      // 原始文件已結束，剩餘的都是新增
      diff.push(`@@ -${i},0 +${j},${modifiedLines.length - j} @@`);
      while (j < modifiedLines.length) {
        diff.push(`+${modifiedLines[j]}`);
        j++;
      }
      break;
    }
    
    if (j >= modifiedLines.length) {
      // 修改後文件已結束，剩餘的都是刪除
      diff.push(`@@ -${i},${originalLines.length - i} +${j},0 @@`);
      while (i < originalLines.length) {
        diff.push(`-${originalLines[i]}`);
        i++;
      }
      break;
    }
    
    if (originalLines[i] === modifiedLines[j]) {
      // 行相同，保持不變
      diff.push(` ${originalLines[i]}`);
      i++;
      j++;
    } else {
      // 行不同，需要生成 hunk
      // 簡單實現：刪除舊行，添加新行
      const hunkStart = i + 1;
      let removedCount = 0;
      let addedCount = 0;
      
      // 嘗試找到匹配的行
      let foundMatch = false;
      for (let k = j; k < Math.min(j + 10, modifiedLines.length); k++) {
        if (originalLines[i] === modifiedLines[k]) {
          // 找到匹配，中間的行都是新增
          addedCount = k - j;
          diff.push(`@@ -${hunkStart},${removedCount + 1} +${j + 1},${addedCount + 1} @@`);
          for (let l = j; l < k; l++) {
            diff.push(`+${modifiedLines[l]}`);
          }
          diff.push(` ${originalLines[i]}`);
          i++;
          j = k + 1;
          foundMatch = true;
          break;
        }
      }
      
      if (!foundMatch) {
        // 沒找到匹配，刪除舊行，添加新行
        removedCount = 1;
        addedCount = 1;
        diff.push(`@@ -${hunkStart},${removedCount} +${j + 1},${addedCount} @@`);
        diff.push(`-${originalLines[i]}`);
        diff.push(`+${modifiedLines[j]}`);
        i++;
        j++;
      }
    }
  }
  
  return diff.join('\n');
}
