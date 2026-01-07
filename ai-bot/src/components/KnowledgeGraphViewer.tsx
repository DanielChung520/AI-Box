/**
 * 代碼功能說明: 知識圖譜可視化組件，使用 AntV G6 渲染知識圖譜
 * 創建日期: 2025-12-10
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-06
 */

import { useEffect, useRef, useState } from 'react';
import { Graph } from '@antv/g6';
import { Network, LayoutGrid, Circle } from 'lucide-react';

interface Triple {
  subject: string;
  subject_type?: string;
  relation: string;
  object: string;
  object_type?: string;
  confidence?: number;
}

interface KnowledgeGraphViewerProps {
  triples: Triple[];
  nodes?: Array<{
    id: string;
    label?: string;
    name?: string;
    type?: string;
    text?: string;
  }>;
  edges?: Array<{
    id?: string;
    source?: string;
    target?: string;
    from?: string;
    to?: string;
    label?: string;
    type?: string;
    relation?: string;
    confidence?: number;
  }>;
  height?: number;
}

type LayoutType = 'force' | 'circular' | 'grid';

// 實體類型顏色映射（擴展版，包含更多顏色）
const ENTITY_TYPE_COLORS: Record<string, string> = {
  'Person': '#4A90E2',        // 藍色
  'Organization': '#50C878',  // 綠色
  'Location': '#FF6B6B',      // 紅色
  'Event': '#FFA500',         // 橙色
  'Document': '#9B59B6',      // 紫色
  'Software': '#3498DB',      // 天藍色
  'Task': '#E74C3C',          // 深紅色
  'Command': '#1ABC9C',       // 青綠色
  'Feature': '#F39C12',       // 金黃色
  'NotionPage': '#E91E63',    // 粉紅色
  'Notion_Workspace': '#9C27B0', // 深紫色
  'Notion_User': '#2196F3',   // 亮藍色
  'Product': '#00BCD4',       // 青色
  'Service': '#8BC34A',       // 淺綠色
  'Technology': '#FF5722',    // 深橙色
  'Company': '#3F51B5',       // 靛藍色
  'Project': '#FF9800',       // 橙黃色
  'Concept': '#9C27B0',       // 紫色
  'Method': '#009688',        // 青綠色
  'Tool': '#795548',          // 棕色
  'Resource': '#607D8B',       // 藍灰色
  'Default': '#95A5A6',       // 灰色
};

// 豐富的顏色調色板（用於未匹配類型的節點）
const COLOR_PALETTE = [
  '#4A90E2', // 藍色
  '#50C878', // 綠色
  '#FF6B6B', // 紅色
  '#FFA500', // 橙色
  '#9B59B6', // 紫色
  '#3498DB', // 天藍色
  '#E74C3C', // 深紅色
  '#1ABC9C', // 青綠色
  '#F39C12', // 金黃色
  '#E91E63', // 粉紅色
  '#00BCD4', // 青色
  '#8BC34A', // 淺綠色
  '#FF5722', // 深橙色
  '#3F51B5', // 靛藍色
  '#FF9800', // 橙黃色
  '#009688', // 青綠色
  '#795548', // 棕色
  '#607D8B', // 藍灰色
  '#CDDC39', // 黃綠色
  '#FFC107', // 琥珀色
  '#FF4081', // 粉紅色
  '#00E676', // 亮綠色
  '#FF1744', // 深紅色
  '#651FFF', // 深紫色
  '#00B8D4', // 亮青色
];

// 根據節點 ID 獲取顏色（用於未匹配類型的節點）
const getColorForNode = (nodeId: string, nodeIndex: number): string => {
  // 使用節點 ID 的哈希值和索引來選擇顏色，確保相同 ID 總是得到相同顏色
  let hash = 0;
  for (let i = 0; i < nodeId.length; i++) {
    hash = ((hash << 5) - hash) + nodeId.charCodeAt(i);
    hash = hash & hash; // 轉換為 32 位整數
  }
  // 結合索引以增加顏色分佈的多樣性
  const combinedHash = (hash + nodeIndex) % COLOR_PALETTE.length;
  const colorIndex = Math.abs(combinedHash);
  return COLOR_PALETTE[colorIndex];
};

export default function KnowledgeGraphViewer({
  triples = [],
  nodes: providedNodes = [],
  edges: providedEdges = [],
  height = 400,
}: KnowledgeGraphViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const isRenderingRef = useRef<boolean>(false);
  const hoveredNodeRef = useRef<any>(null); // 追蹤當前懸停的節點
  const [layoutType, setLayoutType] = useState<LayoutType>('grid'); // 修改時間：2026-01-06 - 默認使用網格布局
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredListNodeId, setHoveredListNodeId] = useState<string | null>(null); // 追蹤列表中被懸停的節點
  const [highlightedTripleIndex, setHighlightedTripleIndex] = useState<number | null>(null); // 修改時間：2026-01-06 - 追蹤需要聚焦顯示的三元組索引
  const tripleListRef = useRef<HTMLDivElement>(null); // 修改時間：2026-01-06 - 三元組列表的引用，用於滾動到指定位置
  const [isDarkMode, setIsDarkMode] = useState(false);

  // 檢測深色模式
  useEffect(() => {
    const checkDarkMode = () => {
      const isDark = document.documentElement.classList.contains('dark') ||
        window.matchMedia('(prefers-color-scheme: dark)').matches;
      setIsDarkMode(isDark);
    };

    checkDarkMode();

    // 監聽主題變化
    const observer = new MutationObserver(checkDarkMode);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });

    // 監聽系統主題變化
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', checkDarkMode);

    return () => {
      observer.disconnect();
      mediaQuery.removeEventListener('change', checkDarkMode);
    };
  }, []);

  // 修改時間：2026-01-06 - 當聚焦的三元組索引變化時，滾動到對應位置
  useEffect(() => {
    if (highlightedTripleIndex !== null && tripleListRef.current) {
      const tripleElements = tripleListRef.current.querySelectorAll('[data-triple-index]');
      const targetElement = Array.from(tripleElements).find(
        (el) => el.getAttribute('data-triple-index') === String(highlightedTripleIndex)
      ) as HTMLElement;

      if (targetElement) {
        // 滾動到目標元素，並添加平滑滾動效果
        targetElement.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }
    }
  }, [highlightedTripleIndex]);

  const [tooltip, setTooltip] = useState<{
    visible: boolean;
    x: number;
    y: number;
    content: {
      label: string;
      entityType: string;
    };
  } | null>(null);

  // 從三元組構建節點和邊（帶編號）
  const buildGraphData = (darkMode: boolean = false): { nodes: any[]; edges: any[]; nodeIndexMap: Map<string, number> } => {
    const nodeMap = new Map<string, any>();
    const edgeList: any[] = [];
    const nodeIndexMap = new Map<string, number>();

    // 如果提供了 nodes 和 edges，直接使用
    if (providedNodes.length > 0 && providedEdges.length > 0) {
      const nodes = providedNodes.map((node, index) => {
        const entityType = node.type || 'Unknown';
        const nodeIndex = index + 1;
        const originalLabel = node.label || node.name || node.text || node.id;

        nodeIndexMap.set(node.id, nodeIndex);

        // 獲取節點顏色：優先使用實體類型顏色，否則使用調色板顏色
        const nodeColor = ENTITY_TYPE_COLORS[entityType] || getColorForNode(node.id, nodeIndex);

        return {
          id: node.id,
          label: `${nodeIndex}`, // 使用編號作為圖形標籤
          type: 'circle',
          data: {
            entityType: entityType,
            originalLabel: originalLabel,
            nodeIndex: nodeIndex,
          },
          style: {
            fill: nodeColor,
            stroke: darkMode ? '#374151' : '#fff',
            lineWidth: 2,
          },
        };
      });

      // 創建節點 ID 集合，用於驗證邊的引用
      // 同時支持完整格式（entities/xxx）和簡化格式（xxx）的 ID
      const nodeIdSet = new Set<string>();
      const nodeIdMap = new Map<string, string>(); // 簡化格式 -> 完整格式的映射

      nodes.forEach(node => {
        const nodeId = node.id;
        nodeIdSet.add(nodeId);

        // 如果節點 ID 是完整格式（entities/xxx），也添加簡化格式（xxx）到映射
        if (nodeId.includes('/')) {
          const simplifiedId = nodeId.split('/').pop() || nodeId;
          nodeIdMap.set(simplifiedId, nodeId);
          // 也將簡化格式添加到集合，以便匹配
          nodeIdSet.add(simplifiedId);
        }
      });

      // 過濾掉引用不存在節點的邊
      const edges = providedEdges
        .map((edge, index) => {
          // 標準化 source 和 target ID
          let sourceId = edge.source || edge.from || '';
          let targetId = edge.target || edge.to || '';

          // 如果 source/target 是簡化格式，嘗試轉換為完整格式
          if (sourceId && !sourceId.includes('/') && nodeIdMap.has(sourceId)) {
            sourceId = nodeIdMap.get(sourceId) || sourceId;
          }
          if (targetId && !targetId.includes('/') && nodeIdMap.has(targetId)) {
            targetId = nodeIdMap.get(targetId) || targetId;
          }

          return {
        id: edge.id || `edge_${index}`,
            source: sourceId,
            target: targetId,
        label: edge.label || edge.type || edge.relation || '',
        style: {
              stroke: darkMode ? '#6b7280' : '#999',
          lineWidth: 1.5,
          endArrow: {
            path: 'M 0,0 L 8,4 L 8,-4 Z',
                fill: darkMode ? '#6b7280' : '#999',
          },
        },
          };
        })
        .filter(edge => {
          // 只保留 source 和 target 都存在於節點列表中的邊
          const sourceExists = nodeIdSet.has(edge.source);
          const targetExists = nodeIdSet.has(edge.target);

          // 只在開發模式下輸出警告（避免生產環境的日誌噪音）
          if (!sourceExists || !targetExists) {
            if (process.env.NODE_ENV === 'development') {
              console.debug(
                '[KnowledgeGraphViewer] Filtering edge with missing node:',
                {
                  source: edge.source,
                  target: edge.target,
                  sourceExists,
                  targetExists,
                  totalNodes: nodes.length,
                  totalEdges: providedEdges.length
                }
              );
            }
          }
          return sourceExists && targetExists;
        });

      return { nodes, edges, nodeIndexMap };
    }

    // 從三元組構建（帶編號）
    triples.forEach((triple, index) => {
      const subject = triple.subject;
      const obj = triple.object;
      const subjectType = triple.subject_type || 'Unknown';
      const objType = triple.object_type || 'Unknown';

      // 添加主體節點
      if (subject && !nodeMap.has(subject)) {
        const nodeIndex = nodeMap.size + 1;
        nodeIndexMap.set(subject, nodeIndex);

        // 獲取節點顏色：優先使用實體類型顏色，否則使用調色板顏色
        const subjectColor = ENTITY_TYPE_COLORS[subjectType] || getColorForNode(subject, nodeIndex);

        nodeMap.set(subject, {
          id: subject,
          label: `${nodeIndex}`,
          type: 'circle',
          data: {
            entityType: subjectType,
            originalLabel: subject,
            nodeIndex: nodeIndex,
          },
          style: {
            fill: subjectColor,
            stroke: darkMode ? '#374151' : '#fff',
            lineWidth: 2,
          },
        });
      }

      // 添加客體節點
      if (obj && !nodeMap.has(obj)) {
        const nodeIndex = nodeMap.size + 1;
        nodeIndexMap.set(obj, nodeIndex);

        // 獲取節點顏色：優先使用實體類型顏色，否則使用調色板顏色
        const objColor = ENTITY_TYPE_COLORS[objType] || getColorForNode(obj, nodeIndex);

        nodeMap.set(obj, {
          id: obj,
          label: `${nodeIndex}`,
          type: 'circle',
          data: {
            entityType: objType,
            originalLabel: obj,
            nodeIndex: nodeIndex,
          },
          style: {
            fill: objColor,
            stroke: darkMode ? '#374151' : '#fff',
            lineWidth: 2,
          },
        });
      }

      // 添加邊
      if (subject && obj && triple.relation) {
        edgeList.push({
          id: `edge_${index}`,
          source: subject,
          target: obj,
          label: triple.relation,
          style: {
            stroke: darkMode ? '#6b7280' : '#999',
            lineWidth: 1.5,
            endArrow: {
              path: 'M 0,0 L 8,4 L 8,-4 Z',
              fill: darkMode ? '#6b7280' : '#999',
            },
          },
        });
      }
    });

    return {
      nodes: Array.from(nodeMap.values()),
      edges: edgeList,
      nodeIndexMap: nodeIndexMap,
    };
  };

  // 初始化圖形
  useEffect(() => {
    if (!containerRef.current) {
      console.warn('[KnowledgeGraphViewer] Container ref is null');
      return;
    }

    // 检查 Graph 是否可用
    if (!Graph) {
      console.error('[KnowledgeGraphViewer] Graph is not available');
      return;
    }

    const graphData = buildGraphData(isDarkMode);
    console.log('[KnowledgeGraphViewer] Graph data:', {
      nodesCount: graphData.nodes.length,
      edgesCount: graphData.edges.length,
      triplesCount: triples.length,
      providedNodesCount: providedNodes.length,
      providedEdgesCount: providedEdges.length,
    });

    if (graphData.nodes.length === 0) {
      console.warn('[KnowledgeGraphViewer] No nodes to render');
      return;
    }

    // 配置佈局
    const layoutConfig: Record<LayoutType, any> = {
      force: {
        type: 'force',
        preventOverlap: true,
        nodeSize: 30, // 缩小40%: 50 * 0.6 = 30
        linkDistance: 150,
        nodeStrength: -300,
        edgeStrength: 0.2,
      },
      circular: {
        type: 'circular',
        radius: Math.min(height / 2 - 50, 200),
        startRadius: 10,
      },
      grid: {
        type: 'grid',
        rows: Math.ceil(Math.sqrt(graphData.nodes.length)),
        cols: Math.ceil(Math.sqrt(graphData.nodes.length)),
      },
    };

    // 確保容器有寬度
    const containerWidth = containerRef.current.offsetWidth || 800;
    const containerHeight = height;

    console.log('[KnowledgeGraphViewer] Container dimensions:', {
      width: containerWidth,
      height: containerHeight,
    });

    // 創建圖形實例
    let graph: any;
    try {
      graph = new Graph({
        container: containerRef.current,
        width: containerWidth,
        height: containerHeight,
        layout: layoutConfig[layoutType],
        background: isDarkMode ? '#111827' : '#ffffff',
        // 啟用動畫效果（如果 G6 v5 支持）
        animation: {
          duration: 200, // 動畫持續時間（毫秒）
          easing: 'ease-in-out', // 動畫緩動函數
        },
        modes: {
          default: ['drag-canvas', 'zoom-canvas', 'drag-node', 'click-select'],
        },
        // 啟用節點交互（G6 v5 可能需要明確啟用）
        node: {
          state: {
            hover: true, // 啟用 hover 狀態
            selected: true, // 啟用 selected 狀態
          },
        },
        defaultNode: {
          type: 'circle',
          size: 24, // 缩小40%: 40 * 0.6 = 24
          labelCfg: {
            style: {
              fill: isDarkMode ? '#e5e7eb' : '#000',
              fontSize: 12,
              fontWeight: 'bold',
            },
            position: 'bottom',
            offset: 5,
          },
          // 添加过渡动画效果
          style: {
            cursor: 'pointer',
          },
        },
        defaultEdge: {
          type: 'line',
          labelCfg: {
            autoRotate: true,
            style: {
              fill: isDarkMode ? '#d1d5db' : '#666',
              fontSize: 10,
              background: {
                fill: isDarkMode ? '#374151' : '#fff',
                stroke: isDarkMode ? '#4b5563' : '#ccc',
                padding: [2, 4, 2, 4],
              },
            },
          },
        },
        nodeStateStyles: {
          selected: {
            stroke: isDarkMode ? '#60a5fa' : '#1890ff',
            lineWidth: 3,
            size: 26.4, // 放大 10%: 24 * 1.1 = 26.4
          },
          hover: {
            stroke: isDarkMode ? '#60a5fa' : '#1890ff',
            lineWidth: 2,
            size: 26.4, // 放大 10%: 24 * 1.1 = 26.4
            // 添加阴影效果，让放大更明显
            shadowBlur: 10,
            shadowColor: isDarkMode ? 'rgba(96, 165, 250, 0.5)' : 'rgba(24, 144, 255, 0.3)',
          },
        },
      } as any);

      // 設置並渲染數據
      graph.setData(graphData);

      // G6 v5 的 render 是异步的，需要等待完成後再註冊事件處理器
      isRenderingRef.current = true;
      graph.render().then(() => {
        isRenderingRef.current = false;
        console.log('[KnowledgeGraphViewer] Graph rendered, registering events...');
        if (graphRef.current === graph && !graph.destroyed) {
          console.log('[KnowledgeGraphViewer] Graph rendered successfully');

          // 在渲染完成後註冊事件處理器，避免競態條件
          try {
            // 節點點擊事件
            graph.on('node:click', (e: any) => {
              try {
                const nodeId = e.item?.getID?.() || e.item?.getModel?.()?.id || null;
                setSelectedNode(nodeId);
                if (e.item) {
                  (graph as any).setItemState?.(e.item, 'selected', true);
                }
              } catch (err) {
                console.error('[KnowledgeGraphViewer] Error handling node click:', err);
              }
            });

            // 畫布點擊事件 - 點擊空白區域時清除 tooltip 和高亮
            graph.on('canvas:click', (e: any) => {
              try {
                // 如果點擊的是畫布空白區域（不是節點或邊），清除 tooltip 和高亮
                const point = e.canvasPoint || e.point || e.canvas || { x: 0, y: 0 };
                const items = (graph as any).getItemsByPoint?.(point.x, point.y) || [];

                // 如果沒有找到任何項目，清除 tooltip 和高亮
                if (items.length === 0) {
                  setTooltip(null);
                  setHighlightedTripleIndex(null); // 修改時間：2026-01-06 - 清除三元組高亮
                  console.log('[KnowledgeGraphViewer] Canvas clicked (blank area), cleared tooltip and highlight');
                }
              } catch (err) {
                console.warn('[KnowledgeGraphViewer] Error handling canvas click:', err);
              }
            });

            // 邊（關係線條）點擊事件 - 顯示 tooltip
            graph.on('edge:click', (e: any) => {
              try {
                const edgeItem = e.item;
                if (!edgeItem) {
                  return;
                }

                const edgeModel = edgeItem.getModel?.() || edgeItem;
                const edgeLabel = edgeModel.label || edgeModel.type || edgeModel.relation || '關係';
                const edgeSource = edgeModel.source || edgeModel.from || '';
                const edgeTarget = edgeModel.target || edgeModel.to || '';

                console.log('[KnowledgeGraphViewer] Edge clicked:', {
                  edgeLabel,
                  edgeSource,
                  edgeTarget,
                  edgeModel,
                });

                // 獲取源節點和目標節點的名稱
                let sourceLabel = edgeSource;
                let targetLabel = edgeTarget;

                // 嘗試從圖中獲取節點數據
                if (edgeSource) {
                  try {
                    const sourceNodeData = (graph as any).getNodeData?.(edgeSource);
                    if (sourceNodeData) {
                      const sourceData = sourceNodeData.data || sourceNodeData;
                      sourceLabel = sourceData.originalLabel || sourceData.name || sourceData.text || edgeSource.split('/').pop() || edgeSource;
                    } else {
                      // 如果無法從圖中獲取，嘗試從 providedNodes 查找
                      const originalSourceNode = providedNodes.find(n => n.id === edgeSource);
                      if (originalSourceNode) {
                        sourceLabel = originalSourceNode.name || originalSourceNode.text || originalSourceNode.label || edgeSource.split('/').pop() || edgeSource;
                      }
                    }
                  } catch (err) {
                    console.warn('[KnowledgeGraphViewer] Failed to get source node data:', err);
                  }
                }

                if (edgeTarget) {
                  try {
                    const targetNodeData = (graph as any).getNodeData?.(edgeTarget);
                    if (targetNodeData) {
                      const targetData = targetNodeData.data || targetNodeData;
                      targetLabel = targetData.originalLabel || targetData.name || targetData.text || edgeTarget.split('/').pop() || edgeTarget;
                    } else {
                      // 如果無法從圖中獲取，嘗試從 providedNodes 查找
                      const originalTargetNode = providedNodes.find(n => n.id === edgeTarget);
                      if (originalTargetNode) {
                        targetLabel = originalTargetNode.name || originalTargetNode.text || originalTargetNode.label || edgeTarget.split('/').pop() || edgeTarget;
                      }
                    }
                  } catch (err) {
                    console.warn('[KnowledgeGraphViewer] Failed to get target node data:', err);
                  }
                }

                // 獲取鼠標位置
                const containerRect = containerRef.current?.getBoundingClientRect();
                let mouseX = 0;
                let mouseY = 0;

                const originalEvent = e.originalEvent || e.event || e.nativeEvent;
                if (originalEvent && (originalEvent.clientX !== undefined || originalEvent.pageX !== undefined)) {
                  mouseX = originalEvent.clientX !== undefined ? originalEvent.clientX : originalEvent.pageX;
                  mouseY = originalEvent.clientY !== undefined ? originalEvent.clientY : originalEvent.pageY;
                }

                // 如果沒有鼠標位置，使用邊的中點位置
                if ((mouseX === 0 && mouseY === 0) && containerRect && edgeModel.x !== undefined && edgeModel.y !== undefined) {
                  mouseX = edgeModel.x + containerRect.left;
                  mouseY = edgeModel.y + containerRect.top;
                }

                // 如果仍然沒有位置，使用容器中心
                if ((mouseX === 0 && mouseY === 0) && containerRect) {
                  mouseX = containerRect.left + containerRect.width / 2;
                  mouseY = containerRect.top + containerRect.height / 2;
                }

                if (mouseX > 0 || mouseY > 0) {
                  setTooltip({
                    visible: true,
                    x: mouseX + 15,
                    y: mouseY + 15,
                    content: {
                      label: `${sourceLabel} --[${edgeLabel}]--> ${targetLabel}`,
                      entityType: '關係',
                    },
                  });

                  // 修改時間：2026-01-06 - 找到對應的三元組索引並聚焦顯示
                  const matchingTripleIndex = triples.findIndex((triple: any) => {
                    // 匹配 subject、object 和 relation
                    const subjectMatch = triple.subject === edgeSource ||
                                       triple.subject === sourceLabel ||
                                       triple.subject.split('/').pop() === edgeSource.split('/').pop() ||
                                       triple.subject.split('/').pop() === sourceLabel.split('/').pop();
                    const objectMatch = triple.object === edgeTarget ||
                                      triple.object === targetLabel ||
                                      triple.object.split('/').pop() === edgeTarget.split('/').pop() ||
                                      triple.object.split('/').pop() === targetLabel.split('/').pop();
                    const relationMatch = triple.relation === edgeLabel ||
                                        triple.relation === edgeModel.type ||
                                        triple.relation === edgeModel.relation;

                    return subjectMatch && objectMatch && relationMatch;
                  });

                  if (matchingTripleIndex !== -1) {
                    setHighlightedTripleIndex(matchingTripleIndex);
                    console.log('[KnowledgeGraphViewer] Found matching triple at index:', matchingTripleIndex);
                  } else {
                    console.log('[KnowledgeGraphViewer] No matching triple found for edge:', {
                      edgeSource,
                      edgeTarget,
                      edgeLabel,
                    });
                  }

                  console.log('[KnowledgeGraphViewer] Edge tooltip displayed:', {
                    sourceLabel,
                    edgeLabel,
                    targetLabel,
                    position: { x: mouseX, y: mouseY },
                  });
                }
              } catch (err) {
                console.error('[KnowledgeGraphViewer] Error handling edge click:', err);
              }
            });

            // 注意：由於 G6 v5 的 API 限制，節點數據中沒有渲染後的 x/y 坐標
            // 因此無法實現圖形區的 hover 檢測。請使用下方節點列表進行交互。

            // 節點懸停事件 - 顯示 tooltip（備用方案，主要使用 canvas 事件）
            // 嘗試多種事件名稱以確保兼容性
            const handleNodeHover = (e: any) => {
              try {
                // 嘗試多種方式獲取節點 item
                let nodeItem = e.item;

                // 如果沒有 item，嘗試從事件對象的其他屬性獲取
                if (!nodeItem) {
                  // 方法1: 從 target 獲取
                  nodeItem = e.target?.item || e.target;

                  // 方法2: 從 data 獲取
                  if (!nodeItem && e.data) {
                    const nodeId = e.data.id || e.data.item?.id;
                    if (nodeId) {
                      nodeItem = (graph as any).findById?.(nodeId);
                    }
                  }

                  // 方法3: 從 id 獲取
                  if (!nodeItem && e.id) {
                    nodeItem = (graph as any).findById?.(e.id);
                  }

                  // 方法4: 從 node 屬性獲取
                  if (!nodeItem && e.node) {
                    nodeItem = e.node;
                  }
                }

                // 只在有 item 時處理，沒有 item 是正常情況（例如在畫布上）
                if (!nodeItem) {
                  return; // 靜默返回，不輸出警告
                }

                // 使用找到的 nodeItem
                e.item = nodeItem;

                // 安全地獲取節點模型（G6 v5 可能使用不同的 API）
                let nodeModel: any = null;
                let nodeId: string | null = null;

                try {
                  // 方法1: 使用 getModel() 方法
                  if (typeof e.item.getModel === 'function') {
                    nodeModel = e.item.getModel();
                    nodeId = nodeModel?.id;
                  }
                  // 方法2: 直接使用 item 作為模型（如果它已經是數據對象）
                  else if (e.item && typeof e.item === 'object' && e.item.id) {
                    nodeModel = e.item;
                    nodeId = e.item.id;
                  }
                  // 方法3: 使用 data 屬性
                  else if (e.item?.data) {
                    nodeModel = e.item.data;
                    nodeId = nodeModel?.id;
                  }
                  // 方法4: 使用 model 屬性
                  else if (e.item?.model) {
                    nodeModel = e.item.model;
                    nodeId = nodeModel?.id;
                  }

                  if (!nodeModel || !nodeId) {
                    return;
                  }
                } catch (modelErr) {
                  return;
                }

                // 方法1: 嘗試設置節點 hover 狀態（G6 v5 標準方式）
                try {
                  // 確保 e.item 是有效的節點對象
                  let nodeInstance = e.item;

                  // 如果 e.item 是數據對象，需要通過 ID 查找節點實例
                  if (!nodeInstance.getModel && nodeId) {
                    nodeInstance = (graph as any).findById?.(nodeId);
                    if (nodeInstance) {
                      e.item = nodeInstance;
                    }
                  }

                  if (nodeInstance && (graph as any).setItemState) {
                    (graph as any).setItemState(nodeInstance, 'hover', true);

                    // 檢查狀態是否設置成功
                    const states = (graph as any).getItemState?.(nodeInstance) || [];

                    // 如果狀態設置成功，觸發重新渲染
                    if (states.includes('hover')) {
                      (graph as any).render?.();
                    }
                  }
                } catch (stateErr) {
                  // 靜默處理錯誤
                }

                // 方法2: 直接更新節點數據和樣式（備用方案）
                try {
                  const hoverSize = 26.4; // 放大 10%: 24 * 1.1 = 26.4

                  // 嘗試多種更新方法
                  let updated = false;

                  // 確保有節點實例（如果 e.item 不是實例，通過 ID 查找）
                  let nodeInstance = e.item;
                  if (!nodeInstance || (typeof nodeInstance.getModel !== 'function' && nodeId)) {
                    nodeInstance = (graph as any).findById?.(nodeId);
                  }

                  // 方法2a: 使用 updateItem
                  if (nodeInstance && (graph as any).updateItem) {
                    try {
                      (graph as any).updateItem(nodeInstance, {
                        style: {
                          ...(nodeModel.style || {}),
                          size: hoverSize,
                          lineWidth: 2,
                          stroke: isDarkMode ? '#60a5fa' : '#1890ff',
                        },
                      });
                      (graph as any).render?.();
                      updated = true;
                    } catch (err) {
                      // 靜默處理錯誤
                    }
                  }

                  // 方法2b: 使用 updateData (G6 v5 需要更新完整的数据结构)
                  if (!updated && (graph as any).updateData) {
                    try {
                      // G6 v5 的 updateData 可能需要完整的节点数据，而不仅仅是 style
                      const currentNodeData = (graph as any).getNodeData?.(nodeId) || nodeModel;
                      const updatedNodeData = {
                        id: nodeId,
                        ...currentNodeData,
                        style: {
                          ...(currentNodeData.style || nodeModel.style || {}),
                          size: hoverSize,
                          lineWidth: 2,
                          stroke: isDarkMode ? '#60a5fa' : '#1890ff',
                          shadowBlur: 10,
                          shadowColor: isDarkMode ? 'rgba(96, 165, 250, 0.5)' : 'rgba(24, 144, 255, 0.3)',
                        },
                      };

                      // G6 v5 的 updateData 可能需要传递数组
                      (graph as any).updateData('node', [updatedNodeData]);

                      // 强制重新渲染 - G6 v5 可能需要调用不同的方法
                      // 尝试多种方式触发重新渲染
                      let renderTriggered = false;

                      // 方法1: 尝试使用 updateLayout
                      if ((graph as any).updateLayout) {
                        try {
                          (graph as any).updateLayout();
                          renderTriggered = true;
                        } catch (layoutErr) {
                          // 靜默處理錯誤
                        }
                      }

                      // 方法2: 尝试使用 render（可能是异步的）
                      if ((graph as any).render) {
                        try {
                          const renderResult = (graph as any).render();
                          if (renderResult && typeof renderResult.then === 'function') {
                            renderResult.then(() => {
                              // 渲染完成
                            }).catch(() => {
                              // 靜默處理錯誤
                            });
                          }
                          renderTriggered = true;
                        } catch (renderErr) {
                          // 靜默處理錯誤
                        }
                      }

                      // 方法3: 尝试使用 draw（G6 v5 可能使用这个）
                      if ((graph as any).draw) {
                        try {
                          (graph as any).draw();
                          renderTriggered = true;
                        } catch (drawErr) {
                          // 靜默處理錯誤
                        }
                      }

                      // 方法4: 如果以上方法都不工作，尝试直接操作 DOM（最后手段）
                      if (!renderTriggered && nodeInstance) {
                        try {
                          // 尝试通过节点实例直接更新样式
                          const nodeElement = (nodeInstance as any).getContainer?.() || (nodeInstance as any).container || (nodeInstance as any).getShape?.();
                          if (nodeElement) {
                            // 查找 circle 元素
                            const shape = nodeElement.querySelector?.('circle') ||
                                         (nodeElement.tagName === 'circle' ? nodeElement : null) ||
                                         nodeElement;

                            if (shape && shape.setAttribute) {
                              shape.setAttribute('r', (hoverSize / 2).toString());
                              shape.setAttribute('stroke-width', '2');
                              shape.setAttribute('stroke', isDarkMode ? '#60a5fa' : '#1890ff');

                              // 添加阴影效果（通过 filter 或 style）
                              if (shape.style) {
                                shape.style.filter = `drop-shadow(0 0 ${10}px ${isDarkMode ? 'rgba(96, 165, 250, 0.5)' : 'rgba(24, 144, 255, 0.3)'})`;
                              }
                              renderTriggered = true;
                            }
                          }
                        } catch (domErr) {
                          // 靜默處理錯誤
                        }
                      }

                      updated = true;
                    } catch (err) {
                      // 靜默處理錯誤
                    }
                  }

                  // 方法2c: 使用 updateNodeData (G6 v5 可能使用這個)
                  if (!updated && (graph as any).updateNodeData) {
                    try {
                      (graph as any).updateNodeData(nodeId, {
                        style: {
                          ...(nodeModel.style || {}),
                          size: hoverSize,
                          lineWidth: 2,
                          stroke: isDarkMode ? '#60a5fa' : '#1890ff',
                        },
                      });
                      (graph as any).render?.();
                      updated = true;
                    } catch (err) {
                      // 靜默處理錯誤
                    }
                  }

                  // 方法2d: 直接修改節點數據並重新設置
                  if (!updated) {
                    try {
                      const nodeData = (graph as any).getNodeData?.(nodeId);
                      if (nodeData) {
                        nodeData.style = {
                          ...(nodeData.style || nodeModel.style || {}),
                          size: hoverSize,
                          lineWidth: 2,
                          stroke: isDarkMode ? '#60a5fa' : '#1890ff',
                        };
                        (graph as any).setNodeData?.(nodeId, nodeData);
                        (graph as any).render?.();
                        updated = true;
                        console.log('[KnowledgeGraphViewer] Updated via setNodeData');
                      }
                    } catch (err) {
                      console.warn('[KnowledgeGraphViewer] setNodeData failed:', err);
                    }
                  }

                  if (updated) {
                    // 保存節點實例到 ref（優先使用找到的實例）
                    hoveredNodeRef.current = nodeInstance || e.item;
                  }
                } catch (updateErr) {
                  // 靜默處理錯誤
                }

                // 獲取節點數據（G6 v5 的節點數據可能存儲在不同的位置）
                // 方法1: 從 nodeModel.data 獲取（G6 v5 可能將數據存儲在這裡）
                let nodeData = nodeModel.data || {};

                // 方法2: 如果 nodeModel.data 不可用，嘗試從 graph 獲取節點數據
                if (!nodeData || Object.keys(nodeData).length === 0) {
                  try {
                    const graphNodeData = (graph as any).getNodeData?.(nodeId);
                    if (graphNodeData) {
                      nodeData = graphNodeData.data || graphNodeData;
                      console.log('[KnowledgeGraphViewer] Retrieved node data from graph.getNodeData:', nodeData);
                    }
                  } catch (err) {
                    console.warn('[KnowledgeGraphViewer] Failed to get node data from graph:', err);
                  }
                }

                // 方法3: 如果仍然沒有數據，嘗試從原始節點列表查找
                if ((!nodeData || Object.keys(nodeData).length === 0) && providedNodes.length > 0) {
                  const originalNode = providedNodes.find(n => n.id === nodeId);
                  if (originalNode) {
                    nodeData = originalNode as any;
                    console.log('[KnowledgeGraphViewer] Retrieved node data from providedNodes:', nodeData);
                  }
                }

                // 優先使用 originalLabel（節點的實際名稱），然後是 name，最後才是 id
                const label = nodeData.originalLabel || nodeData.name || nodeData.text || nodeModel.name || nodeModel.text || nodeModel.label || nodeModel.id || '未知實體';
                const entityType = nodeData.entityType || nodeData.type || nodeModel.type || 'Unknown';

                console.log('[KnowledgeGraphViewer] Tooltip data:', {
                  nodeId,
                  label,
                  entityType,
                  nodeData,
                  nodeModelKeys: Object.keys(nodeModel || {}),
                  nodeModelData: nodeModel.data,
                  providedNodesLength: providedNodes.length,
                });

                // 獲取鼠標位置
                const containerRect = containerRef.current?.getBoundingClientRect();

                // 優先使用全局鼠標位置
                let mouseX = (window as any).mouseX || 0;
                let mouseY = (window as any).mouseY || 0;

                // 方法1: 從事件對象獲取
                const originalEvent = e.originalEvent || e.event || e.nativeEvent;
                if (originalEvent && (originalEvent.clientX !== undefined || originalEvent.pageX !== undefined)) {
                  mouseX = originalEvent.clientX !== undefined ? originalEvent.clientX : originalEvent.pageX;
                  mouseY = originalEvent.clientY !== undefined ? originalEvent.clientY : originalEvent.pageY;
                }

                // 方法2: 使用節點位置 + 容器偏移
                if ((mouseX === 0 && mouseY === 0) && containerRect && nodeModel.x !== undefined && nodeModel.y !== undefined) {
                  mouseX = nodeModel.x + containerRect.left;
                  mouseY = nodeModel.y + containerRect.top;
                }

                // 方法3: 使用畫布坐標轉換
                if ((mouseX === 0 && mouseY === 0) && containerRect) {
                  const canvasPoint = e.canvasPoint || e.canvas || e.point || { x: 0, y: 0 };
                  mouseX = canvasPoint.x + containerRect.left;
                  mouseY = canvasPoint.y + containerRect.top;
                }

                if (mouseX > 0 || mouseY > 0) {
                  setTooltip({
                    visible: true,
                    x: mouseX + 15,
                    y: mouseY + 15,
                    content: {
                      label: label,
                      entityType: entityType,
                    },
                  });
                }
              } catch (err) {
                // 靜默處理錯誤
              }
            };

            // 註冊 G6 節點 hover 事件（嘗試多種事件名稱以確保兼容性）
            try {
              // G6 v5 可能使用不同的事件名稱
              graph.on('node:mouseenter', handleNodeHover);
              graph.on('node:pointerenter', handleNodeHover);
              graph.on('node:mouseover', handleNodeHover);
              graph.on('node:pointerover', handleNodeHover);

              // 嘗試使用 canvas 事件（G6 v5 可能需要在 canvas 上監聽）
              // 這是主要的 hover 檢測方式，因為節點事件可能不工作
              graph.on('canvas:mousemove', (e: any) => {
                // 獲取當前鼠標位置下的節點
                const point = e.canvasPoint || e.point || e.canvas || { x: 0, y: 0 };

                // 如果沒有坐標信息，嘗試從原始事件獲取
                if ((point.x === 0 && point.y === 0) && e.originalEvent) {
                  const containerRect = containerRef.current?.getBoundingClientRect();
                  if (containerRect) {
                    point.x = e.originalEvent.clientX - containerRect.left;
                    point.y = e.originalEvent.clientY - containerRect.top;
                  }
                }

                try {
                  // 嘗試多種方法獲取節點
                  let nodeItem = null;

                  // 方法1: 使用 getItemsByPoint（可以同時獲取節點和邊）
                  let edgeItem = null;
                  if ((graph as any).getItemsByPoint && point.x > 0 && point.y > 0) {
                    try {
                      const items = (graph as any).getItemsByPoint(point.x, point.y) || [];

                      // 優先查找節點
                      nodeItem = items.find((item: any) => {
                        const itemType = item.getType?.() || item.type;
                        return itemType === 'node';
                      });
                      if (nodeItem) {
                        console.log('[KnowledgeGraphViewer] Node found via getItemsByPoint:', nodeItem.getModel()?.id);
                      }

                      // 如果沒有節點，查找邊
                      if (!nodeItem) {
                        edgeItem = items.find((item: any) => {
                          const itemType = item.getType?.() || item.type;
                          return itemType === 'edge' || itemType === 'line';
                        });
                        if (edgeItem) {
                          console.log('[KnowledgeGraphViewer] Edge found via getItemsByPoint:', edgeItem.getModel()?.id);
                        }
                      }
            } catch (err) {
                      console.warn('[KnowledgeGraphViewer] getItemsByPoint failed:', err);
                    }
                  }

                  // 方法2: 使用 getItemByPoint
                  if (!nodeItem && !edgeItem && (graph as any).getItemByPoint && point.x > 0 && point.y > 0) {
                    try {
                      const item = (graph as any).getItemByPoint(point.x, point.y);
                      if (item) {
                        const itemType = item.getType?.() || item.type;
                        if (itemType === 'node') {
                          nodeItem = item;
                          console.log('[KnowledgeGraphViewer] Node found via getItemByPoint:', item.getModel()?.id);
                        } else if (itemType === 'edge' || itemType === 'line') {
                          edgeItem = item;
                          console.log('[KnowledgeGraphViewer] Edge found via getItemByPoint:', item.getModel()?.id);
                        }
                      }
                    } catch (err) {
                      console.warn('[KnowledgeGraphViewer] getItemByPoint failed:', err);
                    }
                  }

                  // 方法3: 使用 findIdByPoint
                  if (!nodeItem && !edgeItem && (graph as any).findIdByPoint && point.x > 0 && point.y > 0) {
                    try {
                      const itemId = (graph as any).findIdByPoint(point.x, point.y);
                      if (itemId) {
                        const item = (graph as any).findById?.(itemId);
                        if (item) {
                          const itemType = item.getType?.() || item.type;
                          if (itemType === 'node') {
                            nodeItem = item;
                            console.log('[KnowledgeGraphViewer] Node found via findIdByPoint:', itemId);
                          } else if (itemType === 'edge' || itemType === 'line') {
                            edgeItem = item;
                            console.log('[KnowledgeGraphViewer] Edge found via findIdByPoint:', itemId);
                          }
                        }
                      }
                    } catch (err) {
                      console.warn('[KnowledgeGraphViewer] findIdByPoint failed:', err);
                    }
                  }

                  // 如果找到節點，觸發 hover 效果
                  if (nodeItem) {
                    // 避免重複觸發同一個節點的 hover
                    const currentNodeId = nodeItem.getModel?.()?.id;
                    if (hoveredNodeRef.current) {
                      const previousNodeId = hoveredNodeRef.current.getModel?.()?.id;
                      if (currentNodeId === previousNodeId) {
                        // 同一個節點，不需要重複處理
                        return;
                      }
                    }

                    handleNodeHover({ item: nodeItem, originalEvent: e.originalEvent, canvasPoint: point });
                  }
                  // 如果找到邊，顯示邊的 tooltip
                  else if (edgeItem) {
                    try {
                      const edgeModel = edgeItem.getModel?.() || edgeItem;
                      const edgeLabel = edgeModel.label || edgeModel.type || edgeModel.relation || '關係';
                      const edgeSource = edgeModel.source || edgeModel.from || '';
                      const edgeTarget = edgeModel.target || edgeModel.to || '';

                      // 獲取源節點和目標節點的名稱
                      let sourceLabel = edgeSource;
                      let targetLabel = edgeTarget;

                      // 嘗試從圖中獲取節點數據
                      if (edgeSource) {
                        try {
                          const sourceNodeData = (graph as any).getNodeData?.(edgeSource);
                          if (sourceNodeData) {
                            const sourceData = sourceNodeData.data || sourceNodeData;
                            sourceLabel = sourceData.originalLabel || sourceData.name || sourceData.text || edgeSource.split('/').pop() || edgeSource;
                          }
                        } catch (err) {
                          // 忽略錯誤，使用默認值
                        }
                      }

                      if (edgeTarget) {
                        try {
                          const targetNodeData = (graph as any).getNodeData?.(edgeTarget);
                          if (targetNodeData) {
                            const targetData = targetNodeData.data || targetNodeData;
                            targetLabel = targetData.originalLabel || targetData.name || targetData.text || edgeTarget.split('/').pop() || edgeTarget;
                          }
                        } catch (err) {
                          // 忽略錯誤，使用默認值
                        }
                      }

                      // 獲取鼠標位置
                      const containerRect = containerRef.current?.getBoundingClientRect();
                      let mouseX = (window as any).mouseX || 0;
                      let mouseY = (window as any).mouseY || 0;

                      const originalEvent = e.originalEvent || e.event || e.nativeEvent;
                      if (originalEvent && (originalEvent.clientX !== undefined || originalEvent.pageX !== undefined)) {
                        mouseX = originalEvent.clientX !== undefined ? originalEvent.clientX : originalEvent.pageX;
                        mouseY = originalEvent.clientY !== undefined ? originalEvent.clientY : originalEvent.pageY;
                      }

                      if ((mouseX === 0 && mouseY === 0) && containerRect) {
                        mouseX = point.x + containerRect.left;
                        mouseY = point.y + containerRect.top;
                      }

                      if (mouseX > 0 || mouseY > 0) {
                        setTooltip({
                          visible: true,
                          x: mouseX + 15,
                          y: mouseY + 15,
                          content: {
                            label: `${sourceLabel} --[${edgeLabel}]--> ${targetLabel}`,
                            entityType: '關係',
                          },
                        });
                      }
                    } catch (err) {
                      // 靜默處理錯誤
                    }
                  }
                  // 如果既沒有節點也沒有邊，清除之前的 hover 狀態
                  else if (hoveredNodeRef.current) {
                    handleNodeLeave({ item: hoveredNodeRef.current });
                    setTooltip(null);
                  } else {
                    // 清除 tooltip
                    setTooltip(null);
                  }
                } catch (err) {
                  console.error('[KnowledgeGraphViewer] Error in canvas:mousemove handler:', err);
                }
              });

            } catch (err) {
              // 靜默處理錯誤
            }

            // 也在畫布上監聽鼠標移動，更新全局鼠標位置
            if (containerRef.current) {
              const updateMousePosition = (e: MouseEvent) => {
                (window as any).mouseX = e.clientX;
                (window as any).mouseY = e.clientY;
              };
              containerRef.current.addEventListener('mousemove', updateMousePosition);

              // 清理函數中移除監聽器
              const cleanup = () => {
                if (containerRef.current) {
                  containerRef.current.removeEventListener('mousemove', updateMousePosition);
                }
              };
              // 將清理函數存儲在 ref 中以便後續使用
              (containerRef.current as any)._cleanupMouseListener = cleanup;
            }

            // 節點移動事件 - 更新 tooltip 位置
            const handleNodeMove = (e: any) => {
              try {
                if (e.item) {
                  const containerRect = containerRef.current?.getBoundingClientRect();
                  const originalEvent = e.originalEvent || e.event || e.nativeEvent;

                  let mouseX = (window as any).mouseX || 0;
                  let mouseY = (window as any).mouseY || 0;

                  if (originalEvent && (originalEvent.clientX !== undefined || originalEvent.pageX !== undefined)) {
                    mouseX = originalEvent.clientX !== undefined ? originalEvent.clientX : originalEvent.pageX;
                    mouseY = originalEvent.clientY !== undefined ? originalEvent.clientY : originalEvent.pageY;
                  }

                  if ((mouseX === 0 && mouseY === 0) && containerRect) {
                    const canvasPoint = e.canvasPoint || e.canvas || e.point || { x: 0, y: 0 };
                    mouseX = canvasPoint.x + containerRect.left;
                    mouseY = canvasPoint.y + containerRect.top;
                  }

                  if (mouseX > 0 || mouseY > 0) {
                    setTooltip((prev) => {
                      if (!prev) return null;
                      return {
                        ...prev,
                        x: mouseX + 15,
                        y: mouseY + 15,
                      };
                    });
                  }
                }
              } catch (err) {
                console.error('[KnowledgeGraphViewer] Error handling node move:', err);
              }
            };

            graph.on('node:mousemove', handleNodeMove);
            graph.on('node:pointermove', handleNodeMove);

            const handleNodeLeave = (e: any) => {
              try {
                if (e.item) {
                  // 方法1: 清除節點 hover 狀態
                  try {
                (graph as any).setItemState?.(e.item, 'hover', false);
                  } catch (stateErr) {
                    // 靜默處理錯誤
                  }

                  // 方法2: 恢復節點原始樣式（備用方案）
                  try {
                    const nodeModelToRestore = e.item.getModel();
                    const originalSize = 24; // 恢復原始大小
                    const originalStyle = nodeModelToRestore.style || {};

                    // 使用 updateItem 或 updateData 恢復節點樣式
                    let restored = false;

                    if ((graph as any).updateItem) {
                      try {
                        (graph as any).updateItem(e.item, {
                          style: {
                            ...originalStyle,
                            size: originalSize,
                            lineWidth: 2,
                            stroke: originalStyle.stroke || (isDarkMode ? '#374151' : '#fff'),
                          },
                        });
                        (graph as any).render?.();
                        restored = true;
                        console.log('[KnowledgeGraphViewer] Restored via updateItem');
                      } catch (err) {
                        console.warn('[KnowledgeGraphViewer] updateItem restore failed:', err);
                      }
                    }

                    if (!restored && (graph as any).updateData) {
                      try {
                        (graph as any).updateData('node', {
                          id: nodeModelToRestore.id,
                          style: {
                            ...originalStyle,
                            size: originalSize,
                            lineWidth: 2,
                            stroke: originalStyle.stroke || (isDarkMode ? '#374151' : '#fff'),
                          },
                        });
                        (graph as any).render?.();
                        restored = true;
                        console.log('[KnowledgeGraphViewer] Restored via updateData');
                      } catch (err) {
                        console.warn('[KnowledgeGraphViewer] updateData restore failed:', err);
                      }
                    }

                    if (!restored && (graph as any).updateNodeData) {
                      try {
                        (graph as any).updateNodeData(nodeModelToRestore.id, {
                          style: {
                            ...originalStyle,
                            size: originalSize,
                            lineWidth: 2,
                            stroke: originalStyle.stroke || (isDarkMode ? '#374151' : '#fff'),
                          },
                        });
                        (graph as any).render?.();
                        restored = true;
                        console.log('[KnowledgeGraphViewer] Restored via updateNodeData');
                      } catch (err) {
                        console.warn('[KnowledgeGraphViewer] updateNodeData restore failed:', err);
                      }
                    }

                    // 樣式已恢復
                  } catch (updateErr) {
                    // 靜默處理錯誤
                  }

                  hoveredNodeRef.current = null;
                  setTooltip(null);
                }
              } catch (err) {
                // 靜默處理錯誤
              }
            };

            // 註冊 G6 節點離開事件（嘗試多種事件名稱以確保兼容性）
            try {
              graph.on('node:mouseleave', handleNodeLeave);
              graph.on('node:pointerleave', handleNodeLeave);
              graph.on('node:mouseout', handleNodeLeave);
              graph.on('node:pointerout', handleNodeLeave);
            } catch (err) {
              // 靜默處理錯誤
            }

            // 畫布點擊事件（取消選中）
            graph.on('canvas:click', () => {
              try {
                setSelectedNode(null);
                // G6 v5: 使用 getNodeData() 獲取節點數據，然後通過 findById 獲取節點對象
                try {
                  const nodeData = (graph as any).getNodeData?.() || [];
                  if (Array.isArray(nodeData)) {
                    nodeData.forEach((nodeDataItem: any) => {
                      if (nodeDataItem?.id) {
                        const node = (graph as any).findById?.(nodeDataItem.id);
                        if (node) {
                          (graph as any).setItemState?.(node, 'selected', false);
                        }
                      }
                    });
                  }
                } catch (getNodesError) {
                  // 如果 getNodeData 不可用，嘗試使用 getNodes
                  try {
                    const nodes = (graph as any).getNodes?.();
                    if (nodes && Array.isArray(nodes)) {
                      nodes.forEach((node: any) => {
                        (graph as any).setItemState?.(node, 'selected', false);
                      });
                    }
                  } catch (fallbackError) {
                    // 如果兩種方法都失敗，靜默處理
                    console.warn('[KnowledgeGraphViewer] Could not clear node selection states');
                  }
                }
              } catch (err) {
                console.error('[KnowledgeGraphViewer] Error handling canvas click:', err);
              }
            });
          } catch (error) {
            console.error('[KnowledgeGraphViewer] Failed to register event handlers:', error);
          }
        }
      }).catch((error: any) => {
        isRenderingRef.current = false;
        if (graphRef.current === graph && !graph.destroyed) {
          console.error('[KnowledgeGraphViewer] Graph render failed:', error);
        }
      });
    } catch (error) {
      console.error('[KnowledgeGraphViewer] Failed to create graph:', error);
      return;
    }

    graphRef.current = graph;

    // 清理函數
    return () => {
      const currentGraph = graphRef.current;

      // 清理鼠標監聽器
      if (containerRef.current && (containerRef.current as any)._cleanupMouseListener) {
        (containerRef.current as any)._cleanupMouseListener();
      }

      // 清理畫布事件監聽器
      const canvasElement = containerRef.current?.querySelector('canvas');
      if (canvasElement && (canvasElement as any)._cleanupCanvasListeners) {
        (canvasElement as any)._cleanupCanvasListeners();
      }

      if (currentGraph && !currentGraph.destroyed) {
        // 等待渲染完成后再销毁
        const destroyGraph = () => {
          if (currentGraph && !currentGraph.destroyed) {
            try {
              currentGraph.destroy();
            } catch (error) {
              console.warn('[KnowledgeGraphViewer] Error destroying graph:', error);
            }
          }
          if (graphRef.current === currentGraph) {
            graphRef.current = null;
          }
        };

        if (isRenderingRef.current) {
          // 如果正在渲染，等待一段时间后再销毁
          setTimeout(destroyGraph, 200);
        } else {
          destroyGraph();
        }
      }

      // 清理 tooltip
      setTooltip(null);
    };
  }, [triples, providedNodes, providedEdges, height, isDarkMode]); // 添加 isDarkMode 依赖，确保深色模式变化时重新创建图形

  // 處理佈局切換 - 使用單獨的 useEffect
  useEffect(() => {
    if (!graphRef.current || graphRef.current.destroyed) {
      return;
    }

    const graphData = buildGraphData(isDarkMode);
    if (graphData.nodes.length === 0) {
      return;
    }

    const layoutConfig: Record<LayoutType, any> = {
      force: {
        type: 'force',
        preventOverlap: true,
        nodeSize: 50,
        linkDistance: 150,
        nodeStrength: -300,
        edgeStrength: 0.2,
      },
      circular: {
        type: 'circular',
        radius: Math.min(height / 2 - 50, 200),
        startRadius: 10,
      },
      grid: {
        type: 'grid',
        rows: Math.ceil(Math.sqrt(graphData.nodes.length)),
        cols: Math.ceil(Math.sqrt(graphData.nodes.length)),
      },
    };

    // G6 v5 使用 updateLayout 方法更新布局
    try {
      const currentGraph = graphRef.current;
      if (currentGraph.updateLayout) {
        currentGraph.updateLayout(layoutConfig[layoutType]);
      } else {
        // 如果 updateLayout 不存在，使用 setOptions 更新布局
        const currentOptions = currentGraph.getOptions();
        currentGraph.setOptions({
          ...currentOptions,
          layout: layoutConfig[layoutType],
        });
        // 重新渲染（异步）
        currentGraph.render().catch((error: any) => {
          if (!currentGraph.destroyed) {
            console.error('[KnowledgeGraphViewer] Failed to render after layout update:', error);
          }
        });
      }
    } catch (error) {
      if (!graphRef.current.destroyed) {
        console.error('[KnowledgeGraphViewer] Failed to update layout:', error);
      }
    }
  }, [layoutType, height]); // 只在布局类型变化时更新

  // 處理深色模式變化 - 更新 G6 圖形背景色
  useEffect(() => {
    if (!graphRef.current || graphRef.current.destroyed) {
      return;
    }

    try {
      const currentGraph = graphRef.current;
      const newBackground = isDarkMode ? '#111827' : '#ffffff';

      // 方法1: 使用 setOptions 更新背景色（G6 v5 推荐方式）
      if (currentGraph.setOptions) {
        const currentOptions = currentGraph.getOptions?.() || {};
        currentGraph.setOptions({
          ...currentOptions,
          background: newBackground,
        });
        // 觸發重新渲染
        currentGraph.render?.().catch((error: any) => {
          if (!currentGraph.destroyed) {
            console.warn('[KnowledgeGraphViewer] Failed to render after background update:', error);
          }
        });
      } else {
        // 方法2: 直接設置背景色並重新渲染
        (currentGraph as any).background = newBackground;
        // 觸發重新渲染
        currentGraph.render?.().catch((error: any) => {
          if (!currentGraph.destroyed) {
            console.warn('[KnowledgeGraphViewer] Failed to render after background update:', error);
          }
        });
      }

      // 方法3: 直接操作 canvas 背景（備用方案）
      const canvas = containerRef.current?.querySelector('canvas');
      if (canvas) {
        // 設置 canvas 的背景色（通過父容器）
        const container = canvas.parentElement;
        if (container) {
          (container as HTMLElement).style.backgroundColor = newBackground;
        }
      }
    } catch (error) {
      if (graphRef.current && !graphRef.current.destroyed) {
        console.error('[KnowledgeGraphViewer] Failed to update background color:', error);
      }
    }
  }, [isDarkMode]); // 只在深色模式变化时更新

  // 處理佈局切換按鈕點擊
  const handleLayoutChange = (newLayout: LayoutType) => {
    setLayoutType(newLayout);
  };

  const graphData = buildGraphData(isDarkMode);
  const nodeIndexMap = graphData.nodeIndexMap;

  if (graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-900">
        <div className="text-center">
          <Network className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p>暫無圖譜數據</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col bg-white dark:bg-gray-950 theme-transition" style={{ height: '100%', minHeight: '700px' }}>
      {/* 工具欄 */}
      <div className="flex items-center justify-between p-2 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-300">佈局:</span>
          <button
            onClick={() => handleLayoutChange('force')}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              layoutType === 'force'
                ? 'bg-blue-500 dark:bg-blue-600 text-white'
                : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600'
            }`}
            title="力導向佈局"
          >
            <Network className="w-4 h-4 inline mr-1" />
            力導向
          </button>
          <button
            onClick={() => handleLayoutChange('circular')}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              layoutType === 'circular'
                ? 'bg-blue-500 dark:bg-blue-600 text-white'
                : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600'
            }`}
            title="圓形佈局"
          >
            <Circle className="w-4 h-4 inline mr-1" />
            圓形
          </button>
          <button
            onClick={() => handleLayoutChange('grid')}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              layoutType === 'grid'
                ? 'bg-blue-500 dark:bg-blue-600 text-white'
                : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600'
            }`}
            title="網格佈局"
          >
            <LayoutGrid className="w-4 h-4 inline mr-1" />
            網格
          </button>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400">
          節點: {graphData.nodes.length} | 邊: {graphData.edges.length}
        </div>
      </div>

      {/* 圖形容器 */}
      <div
        ref={containerRef}
        className="border border-gray-300 dark:border-gray-800 relative flex-shrink-0 bg-white dark:bg-gray-900"
        style={{ width: '100%', height: `${height}px` }}
        onMouseMove={(_e) => {
          // 圖形區的 hover 由於 G6 v5 API 限制（節點數據沒有渲染後的 x/y 坐標）
          // 暫時無法實現。請使用下方的節點列表進行 hover 和選擇操作。
        }}
        onMouseLeave={() => {
          // 清除 tooltip
          setTooltip(null);

          // 清除當前懸停節點的 hover 狀態
          if (hoveredNodeRef.current && graphRef.current && !graphRef.current.destroyed) {
            try {
              (graphRef.current as any)?.setItemState?.(hoveredNodeRef.current, 'hover', false);
              hoveredNodeRef.current = null;
            } catch (err) {
              // 靜默處理錯誤
            }
          }
        }}
      >
        {/* 使用提示 */}

      </div>

      {/* 節點列表和三元組列表 - 左右分布，占满剩余 50% 高度 */}
      <div className="flex gap-3 border-t-2 border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 flex-1 overflow-hidden relative" style={{ zIndex: 1 }}>

        {/* 左側：節點列表 */}
        <div className="flex-1 p-3 overflow-y-auto border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
          <div className="text-sm font-bold mb-3 text-gray-900 dark:text-gray-100 flex items-center gap-2 flex-wrap">
            <span>節點列表 ({graphData.nodes.length})</span>
            {hoveredListNodeId && (
              <span className="text-blue-600 dark:text-blue-400 text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900 rounded animate-pulse">
                懸停: {hoveredListNodeId}
              </span>
            )}
          </div>

          <div className="flex flex-wrap gap-2 bg-gray-50 dark:bg-gray-900/50 p-2 rounded" style={{ minHeight: '60px' }}>
            {graphData.nodes.length > 0 ? (
              graphData.nodes.map((node: any, index: number) => {
                const nodeId = node.id || node.label || `未知-${index}`;
                const isSelected = selectedNode === nodeId;
                const isHovered = hoveredListNodeId === nodeId;
                const nodeData = node.data || {};
                const entityType = nodeData.entityType || node.type || 'Unknown';
                const nodeIndex = nodeData.nodeIndex || index + 1;
                const originalLabel = nodeData.originalLabel || node.id;

                return (
                  <button
                    key={`node-${index}-${nodeId}`}
                    type="button"
                    style={{
                      minWidth: '80px',
                      padding: '6px 12px',
                      fontSize: '13px',
                      fontWeight: '500',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      userSelect: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      backgroundColor: isSelected
                        ? '#3b82f6'
                        : (isHovered
                          ? (isDarkMode ? '#1e40af' : '#dbeafe')
                          : (isDarkMode ? '#1f2937' : '#ffffff')),
                      color: isSelected
                        ? '#ffffff'
                        : (isHovered
                          ? (isDarkMode ? '#f3f4f6' : '#1f2937')
                          : (isDarkMode ? '#f3f4f6' : '#374151')),
                      border: isSelected
                        ? '2px solid #93c5fd'
                        : (isHovered
                          ? '2px solid #60a5fa'
                          : (isDarkMode ? '1px solid #4b5563' : '1px solid #d1d5db')),
                      boxShadow: isHovered || isSelected
                        ? (isDarkMode ? '0 4px 6px -1px rgba(0, 0, 0, 0.3)' : '0 4px 6px -1px rgba(0, 0, 0, 0.1)')
                        : 'none',
                      transform: isHovered ? 'scale(1.05)' : 'scale(1)',
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedNode(isSelected ? null : nodeId);
                    }}
                    onMouseEnter={(e) => {
                      e.stopPropagation();
                      setHoveredListNodeId(nodeId);

                      // 顯示 tooltip
                      const newTooltip = {
                        visible: true,
                        x: e.clientX + 15,
                        y: e.clientY + 15,
                        content: {
                          label: `${nodeIndex}. ${originalLabel}`,
                          entityType: entityType,
                        },
                      };
                      setTooltip(newTooltip);
                    }}
                    onMouseMove={(e) => {
                      e.stopPropagation();
                      // 更新 tooltip 位置
                      setTooltip((prev) => {
                        if (!prev) return null;
                        return {
                          ...prev,
                          visible: true,
                          x: e.clientX + 15,
                          y: e.clientY + 15,
                        };
                      });
                    }}
                    onMouseLeave={(e) => {
                      e.stopPropagation();
                      setHoveredListNodeId(null);

                      // 隱藏 tooltip
                      setTooltip(null);
                    }}
                    title={`${nodeIndex}. ${originalLabel}${entityType !== 'Unknown' ? ` (${entityType})` : ''}`}
                  >
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '20px',
                      height: '20px',
                      borderRadius: '50%',
                      backgroundColor: isSelected || isHovered
                        ? (isDarkMode ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.3)')
                        : (isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'),
                      fontSize: '11px',
                      fontWeight: 'bold',
                    }}>
                      {nodeIndex}
                    </span>
                    <span style={{ flex: 1, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {originalLabel}
                    </span>
                  </button>
                );
              })
            ) : (
              <div className="text-gray-500 dark:text-gray-400 text-sm">暫無節點數據</div>
            )}
          </div>
        </div>

        {/* 右側：三元組列表 */}
        <div className="flex-1 p-3 overflow-y-auto bg-white dark:bg-gray-950" ref={tripleListRef}>
          <div className="text-sm font-bold mb-3 text-gray-900 dark:text-gray-100">
            三元組列表 ({triples.length})
          </div>

          {triples.length > 0 ? (
            <div className="space-y-2">
              {triples.map((triple: any, index: number) => {
                const subjectIndex = nodeIndexMap.get(triple.subject);
                const objectIndex = nodeIndexMap.get(triple.object);
                const isHighlighted = highlightedTripleIndex === index; // 修改時間：2026-01-06 - 檢查是否為聚焦的三元組

                return (
                  <div
                    key={`triple-${index}`}
                    data-triple-index={index} // 修改時間：2026-01-06 - 添加數據屬性用於滾動定位
                    className="p-2 rounded border theme-transition transition-all duration-200 cursor-pointer text-xs"
                    style={{
                      backgroundColor: isHighlighted
                        ? (isDarkMode ? '#1e3a8a' : '#dbeafe')
                        : (isDarkMode ? '#374151' : '#f3f4f6'),
                      borderColor: isHighlighted
                        ? '#3b82f6'
                        : (isDarkMode ? '#4b5563' : '#e5e7eb'),
                      borderWidth: isHighlighted ? '2px' : '1px',
                      boxShadow: isHighlighted
                        ? (isDarkMode ? '0 4px 8px rgba(59, 130, 246, 0.4)' : '0 4px 8px rgba(59, 130, 246, 0.3)')
                        : 'none',
                      transform: isHighlighted ? 'translateX(4px) scale(1.02)' : 'translateX(0) scale(1)',
                    }}
                    onClick={() => {
                      // 修改時間：2026-01-06 - 點擊三元組項時，清除高亮（可選，或者保持高亮）
                      // setHighlightedTripleIndex(null);
                    }}
                    onMouseEnter={(e) => {
                      // 修改時間：2026-01-06 - 只有在不是高亮狀態時才應用 hover 樣式
                      if (!isHighlighted) {
                        (e.currentTarget as HTMLElement).style.backgroundColor = isDarkMode ? '#1e3a8a' : '#dbeafe';
                        (e.currentTarget as HTMLElement).style.borderColor = '#60a5fa';
                        (e.currentTarget as HTMLElement).style.transform = 'translateX(4px)';
                        (e.currentTarget as HTMLElement).style.boxShadow = isDarkMode
                          ? '0 2px 4px rgba(0, 0, 0, 0.3)'
                          : '0 2px 4px rgba(0, 0, 0, 0.1)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      // 修改時間：2026-01-06 - 只有在不是高亮狀態時才恢復默認樣式
                      if (!isHighlighted) {
                        (e.currentTarget as HTMLElement).style.backgroundColor = isDarkMode ? '#374151' : '#f3f4f6';
                        (e.currentTarget as HTMLElement).style.borderColor = isDarkMode ? '#4b5563' : '#e5e7eb';
                        (e.currentTarget as HTMLElement).style.transform = 'translateX(0)';
                        (e.currentTarget as HTMLElement).style.boxShadow = 'none';
                      }
                    }}
                  >
                    <div className="flex items-center gap-1 text-gray-700 dark:text-gray-200">
                      {subjectIndex && (
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-500 dark:bg-blue-600 text-white text-xs font-bold">
                          {subjectIndex}
                        </span>
                      )}
                      <span className="font-semibold">{triple.subject}</span>
                      <span className="text-gray-400 dark:text-gray-500">→</span>
                      <span className="text-green-600 dark:text-green-400 font-medium">{triple.relation}</span>
                      <span className="text-gray-400 dark:text-gray-500">→</span>
                      {objectIndex && (
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-purple-500 dark:bg-purple-600 text-white text-xs font-bold">
                          {objectIndex}
                        </span>
                      )}
                      <span className="font-semibold">{triple.object}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-gray-500 dark:text-gray-400 text-sm">暫無三元組數據</div>
          )}
        </div>

      </div>

      {/* Tooltip - 顯示節點名稱 */}
      {tooltip && tooltip.visible && (
        <div
          className="fixed bg-gray-900 dark:bg-gray-800 text-white text-sm rounded-lg shadow-2xl p-3 border-2 border-blue-500 dark:border-blue-400 z-50"
          style={{
            left: `${tooltip.x}px`,
            top: `${tooltip.y}px`,
            zIndex: 999999,
            position: 'fixed',
            pointerEvents: 'none',
            maxWidth: '300px',
          }}
        >
          <div className="font-bold text-white">
            {tooltip.content.label}
          </div>
          {tooltip.content.entityType && tooltip.content.entityType !== 'Unknown' && (
            <div className="text-gray-300 text-xs mt-1">
              類型: {tooltip.content.entityType}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
