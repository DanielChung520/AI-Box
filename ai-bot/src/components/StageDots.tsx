/**
 * 代碼功能說明: 文件處理階段三色點（SeaweedFS / 向量 / 圖譜）
 * 創建日期: 2026-01-25
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-25
 *
 * 在文件名前顯示三格非常小的淡色紅黃綠點，緊挨著名稱：
 * - 紅：SeaweedFS 完成
 * - 黃：向量完成
 * - 綠：圖譜完成
 * 完成時稍亮，未完成時極淡。
 */

import React from 'react';

export interface StageDotsProps {
  storageOk: boolean;
  vectorOk: boolean;
  graphOk: boolean;
  /** 可選 className（例如與 theme 對齊） */
  className?: string;
}

const DOT_SIZE = 8; // 修改時間：2026-01-25 - 圓點大小增加 50%（4px → 6px）
const GAP = 2;

export default function StageDots({ storageOk, vectorOk, graphOk, className = '' }: StageDotsProps) {
  return (
    <span
      className={`inline-flex items-center flex-shrink-0 ${className}`}
      style={{ gap: GAP }}
      title={`SeaweedFS: ${storageOk ? '完成' : '未完成'} | 向量: ${vectorOk ? '完成' : '未完成'} | 圖譜: ${graphOk ? '完成' : '未完成'}`}
    >
      <span
        className="rounded-full"
        style={{
          width: DOT_SIZE,
          height: DOT_SIZE,
          backgroundColor: storageOk ? 'rgba(239,68,68,0.6)' : 'rgba(239,68,68,0.18)',
        }}
      />
      <span
        className="rounded-full"
        style={{
          width: DOT_SIZE,
          height: DOT_SIZE,
          backgroundColor: vectorOk ? 'rgba(234,179,8,0.6)' : 'rgba(234,179,8,0.18)',
        }}
      />
      <span
        className="rounded-full"
        style={{
          width: DOT_SIZE,
          height: DOT_SIZE,
          backgroundColor: graphOk ? 'rgba(34,197,94,0.6)' : 'rgba(34,197,94,0.18)',
        }}
      />
    </span>
  );
}
