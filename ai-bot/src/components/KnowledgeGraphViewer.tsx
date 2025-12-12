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
  const [layoutType, setLayoutType] = useState<LayoutType>('force');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    visible: boolean;
    x: number;
    y: number;
    content: {
      label: string;
      entityType: string;
    };
  } | null>(null);

  // 從三元組構建節點和邊
  const buildGraphData = (): { nodes: any[]; edges: any[] } => {
    const nodeMap = new Map<string, any>();
    const edgeList: any[] = [];

    // 如果提供了 nodes 和 edges，直接使用
    if (providedNodes.length > 0 && providedEdges.length > 0) {
      const nodes = providedNodes.map((node) => {
        const entityType = node.type || 'Unknown';
        return {
          id: node.id,
          label: node.label || node.name || node.text || node.id,
          type: 'circle', // G6 v5: type 用于节点形状，不是实体类型
          data: {
            entityType: entityType, // 实体类型存储在 data 中
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

      return { nodes, edges };
    }

    // 從三元組構建
    triples.forEach((triple, index) => {
      const subject = triple.subject;
      const obj = triple.object;
      const subjectType = triple.subject_type || 'Unknown';
      const objType = triple.object_type || 'Unknown';

      // 添加主體節點
      if (subject && !nodeMap.has(subject)) {
        nodeMap.set(subject, {
          id: subject,
          label: subject,
          type: 'circle', // G6 v5: type 用于节点形状
          data: {
            entityType: subjectType, // 实体类型存储在 data 中
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
        nodeMap.set(obj, {
          id: obj,
          label: obj,
          type: 'circle', // G6 v5: type 用于节点形状
          data: {
            entityType: objType, // 实体类型存储在 data 中
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
          size: 40,
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

            // 節點懸停事件 - 顯示 tooltip
            graph.on('node:mouseenter', (e: any) => {
              try {
                if (e.item) {
                  graph.setItemState(e.item, 'hover', true);

                  // 獲取節點數據
                  const nodeModel = e.item.getModel();
                  const nodeData = nodeModel.data || {};
                  const label = nodeModel.label || nodeModel.id || '未知實體';
                  const entityType = nodeData.entityType || nodeModel.type || 'Unknown';

                  // 獲取鼠標位置（使用事件坐標）
                  const containerRect = containerRef.current?.getBoundingClientRect();
                  const mouseEvent = e.originalEvent || e.event;

                  if (containerRect && mouseEvent) {
                    setTooltip({
                      visible: true,
                      x: mouseEvent.clientX + 10,
                      y: mouseEvent.clientY + 10,
                      content: {
                        label: label,
                        entityType: entityType,
                      },
                    });
                  } else {
                    // 備用方案：使用畫布坐標
                    const point = e.canvasPoint || e.canvas || { x: 0, y: 0 };
                    if (containerRect) {
                      setTooltip({
                        visible: true,
                        x: point.x + containerRect.left + 10,
                        y: point.y + containerRect.top + 10,
                        content: {
                          label: label,
                          entityType: entityType,
                        },
                      });
                    }
                  }
                }
              } catch (err) {
                console.error('[KnowledgeGraphViewer] Error handling node hover:', err);
              }
            });

            // 節點移動事件 - 更新 tooltip 位置
            graph.on('node:mousemove', (e: any) => {
              try {
                if (e.item) {
                  const mouseEvent = e.originalEvent || e.event;
                  const containerRect = containerRef.current?.getBoundingClientRect();

                  if (mouseEvent && containerRect) {
                    setTooltip((prev) => {
                      if (!prev) return null;
                      return {
                        ...prev,
                        x: mouseEvent.clientX + 10,
                        y: mouseEvent.clientY + 10,
                      };
                    });
                  }
                }
              } catch (err) {
                console.error('[KnowledgeGraphViewer] Error handling node move:', err);
              }
            });

            graph.on('node:mouseleave', (e: any) => {
              try {
                if (e.item) {
                  graph.setItemState(e.item, 'hover', false);
                }
                setTooltip(null);
              } catch (err) {
                console.error('[KnowledgeGraphViewer] Error handling node leave:', err);
              }
            });

            // 畫布點擊事件（取消選中）
            graph.on('canvas:click', () => {
              try {
                setSelectedNode(null);
                const nodes = graph.getNodes();
                if (nodes && nodes.forEach) {
                  nodes.forEach((node: any) => {
                    graph.setItemState(node, 'selected', false);
                  });
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
    <div className="w-full h-full flex flex-col">
      {/* 工具欄 */}
      <div className="flex items-center justify-between p-2 border-b bg-gray-50">
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
        className="border"
        style={{ width: '100%', height: `${height}px` }}
      />

      {/* 選中節點信息 */}
      {selectedNode && (
        <div className="p-2 border-t bg-gray-50 text-xs">
          <span className="font-semibold">選中節點:</span>{' '}
          <span className="text-blue-600">{selectedNode}</span>
        </div>
      )}

      {/* Tooltip - 顯示實體信息 */}
      {tooltip?.visible && (
        <div
          className="fixed z-50 bg-gray-900 text-white text-xs rounded-lg shadow-lg p-2 pointer-events-none"
          style={{
            left: `${tooltip.x}px`,
            top: `${tooltip.y}px`,
            maxWidth: '250px',
          }}
        >
          <div className="font-semibold mb-1 text-white">
            {tooltip.content.label}
          </div>
          <div className="text-gray-300 text-xs">
            <span className="font-medium">實體類型:</span>{' '}
            <span className="text-blue-300">{tooltip.content.entityType}</span>
          </div>
          <div className="text-gray-400 text-xs mt-1 italic">
            NER 實體節點
          </div>
        </div>
      )}
    </div>
  );
}
