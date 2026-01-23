/**
 * 代碼功能說明: 知識圖譜可視化組件 - 優化數據穩定性
 * 創建日期: 2025-12-10
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-23 03:05 UTC+8
 */

import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { Network, LayoutGrid, Circle } from 'lucide-react';
import CytoscapeGraph from './CytoscapeGraph';

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

export default function KnowledgeGraphViewer({
  triples = [],
  nodes: providedNodes = [],
  edges: providedEdges = [],
  height = 400,
}: KnowledgeGraphViewerProps) {
  const [layoutType, setLayoutType] = useState<LayoutType>('force');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredListNodeId, setHoveredListNodeId] = useState<string | null>(null);
  const [highlightedTripleIndex, setHighlightedTripleIndex] = useState<number | null>(null);
  const tripleListRef = useRef<HTMLDivElement>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [tooltip, setTooltip] = useState<{
    visible: boolean;
    x: number;
    y: number;
    content: {
      label: string;
      entityType: string;
    };
  } | null>(null);
  const mousePosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  useEffect(() => {
    const checkDarkMode = () => {
      const isDark = document.documentElement.classList.contains('dark') ||
        window.matchMedia('(prefers-color-scheme: dark)').matches;
      setIsDarkMode(isDark);
    };

    checkDarkMode();

    const observer = new MutationObserver(checkDarkMode);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', checkDarkMode);

    return () => {
      observer.disconnect();
      mediaQuery.removeEventListener('change', checkDarkMode);
    };
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      mousePosRef.current = { x: e.clientX, y: e.clientY };
    };

    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  useEffect(() => {
    if (highlightedTripleIndex !== null && tripleListRef.current) {
      const tripleElements = tripleListRef.current.querySelectorAll('[data-triple-index]');
      const targetElement = Array.from(tripleElements).find(
        (el) => el.getAttribute('data-triple-index') === String(highlightedTripleIndex)
      ) as HTMLElement;

      if (targetElement) {
        targetElement.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }
    }
  }, [highlightedTripleIndex]);

  // 1. 穩定基礎數據
  // 使用 JSON 字符串作為指紋，確保只有數據真正改變時才重新計算
  const dataFingerprint = JSON.stringify({
    triples: triples.map(t => `${t.subject}|${t.relation}|${t.object}`),
    nodes: providedNodes.map(n => n.id),
    edges: providedEdges.map(e => `${e.source}|${e.target}`)
  });

  const graphData = useMemo(() => {
    const nodeMap = new Map<string, any>();
    const edgeList: any[] = [];
    const nodeIndexMap = new Map<string, number>();

    if (providedNodes.length > 0 && providedEdges.length > 0) {
      const nodeIdSet = new Set<string>();
      const nodeIdMap = new Map<string, string>();

      providedNodes.forEach((node) => {
        nodeIdSet.add(node.id);
        if (node.id.includes('/')) {
          const simplifiedId = node.id.split('/').pop() || node.id;
          nodeIdMap.set(simplifiedId, node.id);
          nodeIdSet.add(simplifiedId);
        }
      });

      providedNodes.forEach((node, index) => {
        nodeIndexMap.set(node.id, index + 1);
      });

      providedEdges
        .map((edge, index) => {
          let sourceId = edge.source || edge.from || '';
          let targetId = edge.target || edge.to || '';

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
          };
        })
        .filter(edge => {
          return nodeIdSet.has(edge.source) && nodeIdSet.has(edge.target);
        })
        .forEach((edge, index) => {
          edgeList.push({
            id: edge.id || `edge_${index}`,
            source: edge.source,
            target: edge.target,
            label: edge.label,
          });
        });

      return {
        nodes: providedNodes.map((node, index) => ({
          id: node.id,
          data: {
            entityType: node.type || 'Unknown',
            originalLabel: node.label || node.name || node.text || node.id,
            nodeIndex: index + 1,
          },
        })),
        edges: edgeList,
        nodeIndexMap,
      };
    }

    triples.forEach((triple, index) => {
      const subject = triple.subject;
      const obj = triple.object;
      const subjectType = triple.subject_type || 'Unknown';
      const objType = triple.object_type || 'Unknown';

      if (subject && !nodeMap.has(subject)) {
        const nodeIndex = nodeMap.size + 1;
        nodeIndexMap.set(subject, nodeIndex);
        nodeMap.set(subject, {
          id: subject,
          data: {
            entityType: subjectType,
            originalLabel: subject,
            nodeIndex,
          },
        });
      }

      if (obj && !nodeMap.has(obj)) {
        const nodeIndex = nodeMap.size + 1;
        nodeIndexMap.set(obj, nodeIndex);
        nodeMap.set(obj, {
          id: obj,
          data: {
            entityType: objType,
            originalLabel: obj,
            nodeIndex,
          },
        });
      }

      if (subject && obj && triple.relation) {
        edgeList.push({
          id: `edge_${index}`,
          source: subject,
          target: obj,
          label: triple.relation,
        });
      }
    });

    return {
      nodes: Array.from(nodeMap.values()),
      edges: edgeList,
      nodeIndexMap,
    };
  }, [triples, providedNodes, providedEdges]);

  // 2. 穩定轉換後的數據
  const cytoNodes = useMemo(() => {
    return graphData.nodes.map((node: any) => ({
      id: node.id,
      label: String(graphData.nodeIndexMap.get(node.id) || 1),
      entityType: node.data?.entityType || 'Unknown',
      originalLabel: node.data?.originalLabel || node.id,
    }));
  }, [graphData]);

  const cytoEdges = useMemo(() => {
    return graphData.edges.map((edge: any, index: number) => ({
      id: edge.id || `edge_${index}`,
      source: edge.source,
      target: edge.target,
      label: edge.label || '',
    }));
  }, [graphData]);

  // 3. 穩定回調函數
  const handleNodeClick = useCallback((nodeId: string) => {
    setSelectedNode(nodeId);
    setHoveredListNodeId(nodeId);
  }, []);

  const handleEdgeClick = useCallback((edgeData: any) => {
    const matchingTripleIndex = triples.findIndex((triple: any) => {
      const subjectMatch = triple.subject === edgeData.source ||
                         triple.subject === edgeData.source.split('/').pop();
      const objectMatch = triple.object === edgeData.target ||
                        triple.object === edgeData.target.split('/').pop();
      const relationMatch = triple.relation === edgeData.label;
      return subjectMatch && objectMatch && relationMatch;
    });
    if (matchingTripleIndex !== -1) {
      setHighlightedTripleIndex(matchingTripleIndex);
    }
  }, [triples]);

  const handleNodeHover = useCallback((nodeData: any) => {
    if (nodeData) {
      setTooltip({
        visible: true,
        x: mousePosRef.current.x + 15,
        y: mousePosRef.current.y + 15,
        content: {
          label: `${nodeData.label}. ${nodeData.originalLabel}`,
          entityType: nodeData.entityType,
        },
      });
    } else {
      setTooltip(null);
    }
  }, []);

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
      <div className="flex items-center justify-between p-2 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-300">佈局:</span>
          <div className="flex gap-0.5 p-0.5 bg-gray-200 dark:bg-gray-800 rounded-lg">
            <button
              onClick={() => setLayoutType('force')}
              className={`px-3 py-1 text-xs rounded-md transition-all flex items-center gap-1 ${
                layoutType === 'force'
                  ? 'bg-blue-500 dark:bg-blue-600 text-white shadow-md'
                  : 'bg-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-700'
              }`}
              title="力導向佈局"
            >
              <Network className="w-3.5 h-3.5" />
              <span>力導向</span>
            </button>
            <button
              onClick={() => setLayoutType('circular')}
              className={`px-3 py-1 text-xs rounded-md transition-all flex items-center gap-1 ${
                layoutType === 'circular'
                  ? 'bg-blue-500 dark:bg-blue-600 text-white shadow-md'
                  : 'bg-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-700'
              }`}
              title="圓形佈局"
            >
              <Circle className="w-3.5 h-3.5" />
              <span>圓形</span>
            </button>
            <button
              onClick={() => setLayoutType('grid')}
              className={`px-3 py-1 text-xs rounded-md transition-all flex items-center gap-1 ${
                layoutType === 'grid'
                  ? 'bg-blue-500 dark:bg-blue-600 text-white shadow-md'
                  : 'bg-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-700'
              }`}
              title="網格佈局"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>網格</span>
            </button>
          </div>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400">
          節點: {graphData.nodes.length} | 邊: {graphData.edges.length}
        </div>
      </div>

      <CytoscapeGraph
        nodes={cytoNodes}
        edges={cytoEdges}
        height={height}
        layoutType={layoutType}
        isDarkMode={isDarkMode}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        onNodeHover={handleNodeHover}
      />

      <div className="flex gap-3 border-t-2 border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 flex-1 overflow-hidden relative" style={{ zIndex: 1 }}>
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
              graphData.nodes.map((node: any) => {
                const nodeId = node.id;
                const isSelected = selectedNode === nodeId;
                const isHovered = hoveredListNodeId === nodeId;
                const nodeData = node.data || {};
                const entityType = nodeData.entityType || 'Unknown';
                const nodeIndex = nodeData.nodeIndex || 1;
                const originalLabel = nodeData.originalLabel || node.id;

                return (
                  <button
                    key={`node-${nodeId}`}
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
                      setTooltip({
                        visible: true,
                        x: e.clientX + 15,
                        y: e.clientY + 15,
                        content: {
                          label: `${nodeIndex}. ${originalLabel}`,
                          entityType: entityType,
                        },
                      });
                    }}
                    onMouseMove={(e) => {
                      e.stopPropagation();
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

        <div className="flex-1 p-3 overflow-y-auto bg-white dark:bg-gray-950" ref={tripleListRef}>
          <div className="text-sm font-bold mb-3 text-gray-900 dark:text-gray-100">
            三元組列表 ({triples.length})
          </div>

          {triples.length > 0 ? (
            <div className="space-y-2">
              {triples.map((triple: any, index: number) => {
                const subjectIndex = graphData.nodeIndexMap.get(triple.subject);
                const objectIndex = graphData.nodeIndexMap.get(triple.object);
                const isHighlighted = highlightedTripleIndex === index;

                return (
                  <div
                    key={`triple-${index}`}
                    data-triple-index={index}
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
                    onMouseEnter={(e) => {
                      if (!isHighlighted) {
                        (e.currentTarget as HTMLElement).style.backgroundColor = isDarkMode ? '#1e3a8a' : '#dbeafe';
                        (e.currentTarget as HTMLElement).style.borderColor = '#60a5fa';
                        (e.currentTarget as HTMLElement).style.transform = 'translateX(4px)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isHighlighted) {
                        (e.currentTarget as HTMLElement).style.backgroundColor = isDarkMode ? '#374151' : '#f3f4f6';
                        (e.currentTarget as HTMLElement).style.borderColor = isDarkMode ? '#4b5563' : '#e5e7eb';
                        (e.currentTarget as HTMLElement).style.transform = 'translateX(0)';
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
