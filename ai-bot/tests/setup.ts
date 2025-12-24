// 代碼功能說明: 測試環境設置
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import '@testing-library/jest-dom';
import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// 每個測試後清理
afterEach(() => {
  cleanup();
});
