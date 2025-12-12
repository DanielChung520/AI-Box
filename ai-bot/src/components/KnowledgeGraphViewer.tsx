/**
 * 代碼功能說明: 知識圖譜可視化組件，使用 AntV G6 渲染知識圖譜
 * 創建日期: 2025-12-10
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-10
 */

import React, { useEffect, useRef, useState } from 'react';
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

// 實體類型顏色映射
const ENTITY_TYPE_COLORS: Record<string, string> = {
  'Person': '#4A90E2',
  'Organization': '#50C878',
  'Location': '#FF6B6B',
  'Event': '#FFA500',
  'Document': '#9B59B6',
  'Software': '#3498DB',
  'Task': '#E74C3C',
  'Command': '#1ABC9C',
  'Feature': '#F39C12',
  'NotionPage': '#E91E63',
  'Notion_Workspace': '#9C27B0',
  'Notion_User': '#2196F3',
  'Default': '#95A5A6',
};

export default function KnowledgeGraphViewer({
  triples = [],
  nodes: providedNodes = [],
  edges: providedEdges = [],
  height = 400,
}: KnowledgeGraphViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const isRenderingRef = useRef<boolean>(false);
  const hoveredNodeRef = useRef<any>(null); // 追蹤當前懸停的節點
  const [layoutType, setLayoutType] = useState<LayoutType>('force');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredListNodeId, setHoveredListNodeId] = useState<string | null>(null); // 追蹤列表中被懸停的節點
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
  const buildGraphData = (): { nodes: any[]; edges: any[]; nodeIndexMap: Map<string, number> } => {
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
            fill: ENTITY_TYPE_COLORS[entityType] || ENTITY_TYPE_COLORS['Default'],
            stroke: '#fff',
            lineWidth: 2,
          },
        };
      });

      const edges = providedEdges.map((edge, index) => ({
        id: edge.id || `edge_${index}`,
        source: edge.source || edge.from || '',
        target: edge.target || edge.to || '',
        label: edge.label || edge.type || edge.relation || '',
        style: {
          stroke: '#999',
          lineWidth: 1.5,
          endArrow: {
            path: 'M 0,0 L 8,4 L 8,-4 Z',
            fill: '#999',
          },
        },
      }));

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
            fill: ENTITY_TYPE_COLORS[subjectType] || ENTITY_TYPE_COLORS['Default'],
            stroke: '#fff',
            lineWidth: 2,
          },
        });
      }

      // 添加客體節點
      if (obj && !nodeMap.has(obj)) {
        const nodeIndex = nodeMap.size + 1;
        nodeIndexMap.set(obj, nodeIndex);

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
            fill: ENTITY_TYPE_COLORS[objType] || ENTITY_TYPE_COLORS['Default'],
            stroke: '#fff',
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
            stroke: '#999',
            lineWidth: 1.5,
            endArrow: {
              path: 'M 0,0 L 8,4 L 8,-4 Z',
              fill: '#999',
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

    const graphData = buildGraphData();
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
    let graph: Graph;
    try {
      graph = new Graph({
        container: containerRef.current,
        width: containerWidth,
        height: containerHeight,
        layout: layoutConfig[layoutType],
        modes: {
          default: ['drag-canvas', 'zoom-canvas', 'drag-node', 'click-select'],
        },
        defaultNode: {
          type: 'circle',
          size: 24, // 缩小40%: 40 * 0.6 = 24
          labelCfg: {
            style: {
              fill: '#000',
              fontSize: 12,
              fontWeight: 'bold',
            },
            position: 'bottom',
            offset: 5,
          },
        },
        defaultEdge: {
          type: 'line',
          labelCfg: {
            autoRotate: true,
            style: {
              fill: '#666',
              fontSize: 10,
              background: {
                fill: '#fff',
                stroke: '#ccc',
                padding: [2, 4, 2, 4],
              },
            },
          },
        },
        nodeStateStyles: {
          selected: {
            stroke: '#1890ff',
            lineWidth: 3,
          },
          hover: {
            stroke: '#1890ff',
            lineWidth: 2,
          },
        },
      });

      // 設置並渲染數據
      graph.setData(graphData);

      // G6 v5 的 render 是异步的，需要等待完成後再註冊事件處理器
      isRenderingRef.current = true;
      graph.render().then(() => {
        isRenderingRef.current = false;
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
                  graph.setItemState(e.item, 'selected', true);
                }
              } catch (err) {
                console.error('[KnowledgeGraphViewer] Error handling node click:', err);
              }
            });

            // 注意：由於 G6 v5 的 API 限制，節點數據中沒有渲染後的 x/y 坐標
            // 因此無法實現圖形區的 hover 檢測。請使用下方節點列表進行交互。

            // 節點懸停事件 - 顯示 tooltip（備用方案，主要使用 canvas 事件）
            // 嘗試多種事件名稱以確保兼容性
            const handleNodeHover = (e: any) => {
              try {
                // 只在有 item 時處理，沒有 item 是正常情況（例如在畫布上）
                if (!e.item) {
                  return; // 靜默返回，不輸出警告
                }

                graph.setItemState(e.item, 'hover', true);

                // 獲取節點數據
                const nodeModel = e.item.getModel();
                const nodeData = nodeModel.data || {};
                const label = nodeModel.label || nodeModel.id || '未知實體';
                const entityType = nodeData.entityType || nodeModel.type || 'Unknown';

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
                console.error('[KnowledgeGraphViewer] Error handling node hover:', err);
              }
            };

            // 註冊 G6 事件（備用方案）
            // 注意：這些事件可能在某些情況下不會觸發，所以主要依賴 canvas 事件監聽器
            try {
              graph.on('node:mouseenter', handleNodeHover);
            } catch (err) {
              console.warn('[KnowledgeGraphViewer] Failed to register node:mouseenter:', err);
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
                  graph.setItemState(e.item, 'hover', false);
                  setTooltip(null);
                }
              } catch (err) {
                console.error('[KnowledgeGraphViewer] Error handling node leave:', err);
              }
            };

            // 註冊 G6 事件（備用方案）
            try {
              graph.on('node:mouseleave', handleNodeLeave);
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
                          graph.setItemState(node, 'selected', false);
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
                        graph.setItemState(node, 'selected', false);
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
      }).catch((error) => {
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
  }, [triples, providedNodes, providedEdges, height]); // 移除 layoutType，单独处理布局切换

  // 處理佈局切換 - 使用單獨的 useEffect
  useEffect(() => {
    if (!graphRef.current || graphRef.current.destroyed) {
      return;
    }

    const graphData = buildGraphData();
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

  // 處理佈局切換按鈕點擊
  const handleLayoutChange = (newLayout: LayoutType) => {
    setLayoutType(newLayout);
  };

  const graphData = buildGraphData();
  const nodeIndexMap = graphData.nodeIndexMap;

  if (graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <Network className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p>暫無圖譜數據</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col" style={{ height: '100%', minHeight: '700px' }}>
      {/* 工具欄 */}
      <div className="flex items-center justify-between p-2 border-b bg-gray-50 dark:bg-gray-800 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">佈局:</span>
          <button
            onClick={() => handleLayoutChange('force')}
            className={`px-3 py-1 text-xs rounded ${
              layoutType === 'force'
                ? 'bg-blue-500 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            }`}
            title="力導向佈局"
          >
            <Network className="w-4 h-4 inline mr-1" />
            力導向
          </button>
          <button
            onClick={() => handleLayoutChange('circular')}
            className={`px-3 py-1 text-xs rounded ${
              layoutType === 'circular'
                ? 'bg-blue-500 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            }`}
            title="圓形佈局"
          >
            <Circle className="w-4 h-4 inline mr-1" />
            圓形
          </button>
          <button
            onClick={() => handleLayoutChange('grid')}
            className={`px-3 py-1 text-xs rounded ${
              layoutType === 'grid'
                ? 'bg-blue-500 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            }`}
            title="網格佈局"
          >
            <LayoutGrid className="w-4 h-4 inline mr-1" />
            網格
          </button>
        </div>
        <div className="text-xs text-gray-500">
          節點: {graphData.nodes.length} | 邊: {graphData.edges.length}
        </div>
      </div>

      {/* 圖形容器 */}
      <div
        ref={containerRef}
        className="border relative flex-shrink-0"
        style={{ width: '100%', height: `${height}px` }}
        onMouseMove={(e) => {
          // 圖形區的 hover 由於 G6 v5 API 限制（節點數據沒有渲染後的 x/y 坐標）
          // 暫時無法實現。請使用下方的節點列表進行 hover 和選擇操作。
        }}
        onMouseLeave={() => {
          // 清除 tooltip
          setTooltip(null);

          // 清除當前懸停節點的 hover 狀態
          if (hoveredNodeRef.current && graphRef.current && !graphRef.current.destroyed) {
            try {
              graphRef.current.setItemState(hoveredNodeRef.current, 'hover', false);
              hoveredNodeRef.current = null;
            } catch (err) {
              // 靜默處理錯誤
            }
          }
        }}
      >
        {/* 使用提示 */}
        <div className="absolute top-2 left-1/2 transform -translate-x-1/2 bg-blue-500/90 text-white text-sm px-4 py-2 rounded-lg z-10 pointer-events-none shadow-lg">
          💡 提示：使用下方節點列表查看節點信息
        </div>
      </div>

      {/* 節點列表和三元組列表 - 左右分布，占满剩余 50% 高度 */}
      <div className="flex gap-3 border-t-2 bg-white dark:bg-gray-900 flex-1 overflow-hidden relative" style={{ zIndex: 1 }}>

        {/* 左側：節點列表 */}
        <div className="flex-1 p-3 overflow-y-auto border-r dark:border-gray-700">
          <div className="text-sm font-bold mb-3 text-gray-900 dark:text-gray-100 flex items-center gap-2 flex-wrap">
            <span>節點列表 ({graphData.nodes.length})</span>
            {hoveredListNodeId && (
              <span className="text-blue-600 dark:text-blue-400 text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900 rounded animate-pulse">
                懸停: {hoveredListNodeId}
              </span>
            )}
          </div>

          <div className="flex flex-wrap gap-2 bg-gray-50 dark:bg-gray-800 p-2 rounded" style={{ minHeight: '60px' }}>
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
                      backgroundColor: isSelected ? '#3b82f6' : (isHovered ? '#dbeafe' : '#ffffff'),
                      color: isSelected ? '#ffffff' : (isHovered ? '#1f2937' : '#374151'),
                      border: isSelected ? '2px solid #93c5fd' : (isHovered ? '2px solid #60a5fa' : '1px solid #d1d5db'),
                      boxShadow: isHovered || isSelected ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
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
                      backgroundColor: isSelected || isHovered ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.1)',
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
              <div className="text-gray-500 text-sm">暫無節點數據</div>
            )}
          </div>
        </div>

        {/* 右側：三元組列表 */}
        <div className="flex-1 p-3 overflow-y-auto">
          <div className="text-sm font-bold mb-3 text-gray-900 dark:text-gray-100">
            三元組列表 ({triples.length})
          </div>

          {triples.length > 0 ? (
            <div className="space-y-2">
              {triples.map((triple: any, index: number) => {
                const subjectIndex = nodeIndexMap.get(triple.subject);
                const objectIndex = nodeIndexMap.get(triple.object);

                return (
                  <div
                    key={`triple-${index}`}
                    className="p-2 rounded border theme-transition transition-all duration-200 cursor-pointer text-xs"
                    style={{
                      backgroundColor: 'var(--bg-secondary, #f3f4f6)',
                      borderColor: 'var(--border-primary, #e5e7eb)',
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.backgroundColor = '#dbeafe';
                      (e.currentTarget as HTMLElement).style.borderColor = '#60a5fa';
                      (e.currentTarget as HTMLElement).style.transform = 'translateX(4px)';
                      (e.currentTarget as HTMLElement).style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.1)';
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-secondary, #f3f4f6)';
                      (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-primary, #e5e7eb)';
                      (e.currentTarget as HTMLElement).style.transform = 'translateX(0)';
                      (e.currentTarget as HTMLElement).style.boxShadow = 'none';
                    }}
                  >
                    <div className="flex items-center gap-1 text-gray-700 dark:text-gray-300">
                      {subjectIndex && (
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-500 text-white text-xs font-bold">
                          {subjectIndex}
                        </span>
                      )}
                      <span className="font-semibold">{triple.subject}</span>
                      <span className="text-gray-400">→</span>
                      <span className="text-green-600 dark:text-green-400 font-medium">{triple.relation}</span>
                      <span className="text-gray-400">→</span>
                      {objectIndex && (
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-purple-500 text-white text-xs font-bold">
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
            <div className="text-gray-500 text-sm">暫無三元組數據</div>
          )}
        </div>

      </div>

      {/* Tooltip - 顯示節點名稱 */}
      {tooltip && tooltip.visible && (
        <div
          className="fixed bg-gray-900 text-white text-sm rounded-lg shadow-2xl p-3 border-2 border-blue-500"
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
