/**
 * 代碼功能說明: Cytoscape.js 圖譜 Hook - 管理 Cytoscape 圖形實例
 * 創建日期: 2026-01-23
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-23
 */

import { useEffect, useRef, useState, useCallback } from 'react';

interface NodeData {
  id: string;
  label: string;
  entityType: string;
  originalLabel: string;
}

interface EdgeData {
  id: string;
  source: string;
  target: string;
  label: string;
}

interface UseCytoscapeGraphOptions {
  nodes: NodeData[];
  edges: EdgeData[];
  height: number;
  layoutType: 'force' | 'circular' | 'grid';
  isDarkMode: boolean;
  onNodeClick?: (nodeId: string) => void;
  onEdgeClick?: (edgeData: { source: string; target: string; label: string }) => void;
}

interface UseCytoscapeGraphReturn {
  containerRef: React.RefObject<HTMLDivElement>;
  cy: any;
  isReady: boolean;
  error: string | null;
  runLayout: (layoutType: 'force' | 'circular' | 'grid') => void;
}

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
  'Product': '#00BCD4',
  'Service': '#8BC34A',
  'Technology': '#FF5722',
  'Company': '#3F51B5',
  'Project': '#FF9800',
  'Concept': '#9C27B0',
  'Method': '#009688',
  'Tool': '#795548',
  'Resource': '#607D8B',
  'Default': '#95A5A6',
};

const COLOR_PALETTE = [
  '#4A90E2', '#50C878', '#FF6B6B', '#FFA500', '#9B59B6',
  '#3498DB', '#E74C3C', '#1ABC9C', '#F39C12', '#E91E63',
  '#00BCD4', '#8BC34A', '#FF5722', '#3F51B5', '#FF9800',
  '#009688', '#795548', '#607D8B', '#CDDC39', '#FFC107',
  '#FF4081', '#00E676', '#FF1744', '#651FFF', '#00B8D4',
];

const getColorForNode = (nodeId: string, nodeIndex: number): string => {
  let hash = 0;
  for (let i = 0; i < nodeId.length; i++) {
    hash = ((hash << 5) - hash) + nodeId.charCodeAt(i);
    hash = hash & hash;
  }
  const combinedHash = (hash + nodeIndex) % COLOR_PALETTE.length;
  const colorIndex = Math.abs(combinedHash);
  return COLOR_PALETTE[colorIndex];
};

const getNodeColor = useCallback((entityType: string, nodeId: string, nodeIndex: number): string => {
  return ENTITY_TYPE_COLORS[entityType] || getColorForNode(nodeId, nodeIndex);
}, []);

export function useCytoscapeGraph({
  nodes,
  edges,
  height,
  layoutType,
  isDarkMode,
  onNodeClick,
  onEdgeClick,
}: UseCytoscapeGraphOptions): UseCytoscapeGraphReturn {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runLayout = useCallback((type: 'force' | 'circular' | 'grid') => {
    if (!cyRef.current) return;

    const layoutConfig: Record<string, any> = {
      force: {
        name: 'cose-bilkent',
        animate: true,
        animationDuration: 500,
        nodeRepulsion: 4500,
        idealEdgeLength: 100,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0,
      },
      circular: {
        name: 'circle',
        animate: true,
        animationDuration: 500,
        radius: Math.min(height / 2 - 50, 200),
      },
      grid: {
        name: 'grid',
        animate: true,
        animationDuration: 500,
        rows: Math.ceil(Math.sqrt(nodes.length)),
        cols: Math.ceil(Math.sqrt(nodes.length)),
      },
    };

    const layout = cyRef.current.layout(layoutConfig[type]);
    layout.run();
  }, [nodes.length, height]);

  useEffect(() => {
    if (!containerRef.current || nodes.length === 0) {
      setIsReady(false);
      return;
    }

    let isMounted = true;

    const initCytoscape = async () => {
      try {
        const cytoscapeModule = await import('cytoscape');
        const coseBilkentModule = await import('cytoscape-cose-bilkent');
        const cytoscape = cytoscapeModule.default;
        const coseBilkent = coseBilkentModule.default;

        cytoscape.use(coseBilkent);

        if (!isMounted || !containerRef.current) return;

        setError(null);

        const nodeElements = nodes.map((node, index) => {
          const color = getNodeColor(node.entityType, node.id, index + 1);
          return {
            group: 'nodes' as const,
            data: {
              id: node.id,
              label: node.originalLabel,
              entityType: node.entityType,
              color: color,
            },
            style: {
              'background-color': color,
              'label': `${index + 1}`,
              'color': isDarkMode ? '#e5e7eb' : '#000',
              'font-size': '12px',
              'font-weight': 'bold',
              'text-valign': 'bottom',
              'text-halign': 'center',
              'text-margin-y': 5,
              'width': 30,
              'height': 30,
              'border-width': 2,
              'border-color': isDarkMode ? '#374151' : '#fff',
            },
          };
        });

        const edgeElements = edges.map((edge, index) => ({
          group: 'edges' as const,
          data: {
            id: edge.id || `edge_${index}`,
            source: edge.source,
            target: edge.target,
            label: edge.label,
          },
          style: {
            'width': 1.5,
            'line-color': isDarkMode ? '#6b7280' : '#999',
            'target-arrow-color': isDarkMode ? '#6b7280' : '#999',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': edge.label,
            'font-size': '10px',
            'text-rotation': 'autorotate',
            'text-background-color': isDarkMode ? '#374151' : '#fff',
            'text-background-opacity': 1,
            'text-background-padding': '3px',
            'color': isDarkMode ? '#d1d5db' : '#666',
          },
        }));

        const cy = cytoscape({
          container: containerRef.current,
          elements: [...nodeElements, ...edgeElements] as any,
          style: [
            {
              selector: 'node:selected',
              style: {
                'border-width': 3,
                'border-color': isDarkMode ? '#60a5fa' : '#1890ff',
                'width': 33,
                'height': 33,
              },
            },
            {
              selector: 'edge:selected',
              style: {
                'line-color': isDarkMode ? '#60a5fa' : '#1890ff',
                'target-arrow-color': isDarkMode ? '#60a5fa' : '#1890ff',
                'width': 3,
              },
            },
          ],
          layout: {
            name: layoutType === 'force' ? 'cose-bilkent' : layoutType === 'circular' ? 'circle' : 'grid',
          },
          wheelSensitivity: 0.2,
          minZoom: 0.1,
          maxZoom: 10,
        });

        cyRef.current = cy;

        cy.on('tap', 'node', (evt: any) => {
          const nodeId = evt.target.id();
          if (onNodeClick) {
            onNodeClick(nodeId);
          }
        });

        cy.on('tap', 'edge', (evt: any) => {
          const edgeData = evt.target.data();
          if (onEdgeClick) {
            onEdgeClick({
              source: edgeData.source,
              target: edgeData.target,
              label: edgeData.label || '',
            });
          }
        });

        cy.on('tap', (evt: any) => {
          if (evt.target === cy) {
            if (onNodeClick) {
              onNodeClick('');
            }
          }
        });

        setIsReady(true);
        console.log('[useCytoscapeGraph] Cytoscape initialized with', nodes.length, 'nodes and', edges.length, 'edges');

      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to initialize Cytoscape');
          console.error('[useCytoscapeGraph] Error:', err);
        }
      }
    };

    initCytoscape();

    return () => {
      isMounted = false;
      if (cyRef.current) {
        try {
          cyRef.current.destroy();
        } catch (e) {
          console.warn('[useCytoscapeGraph] Error destroying graph:', e);
        }
        cyRef.current = null;
      }
    };
  }, [nodes, edges, isDarkMode, getNodeColor, layoutType, onNodeClick, onEdgeClick]);

  return {
    containerRef,
    cy: cyRef.current,
    isReady,
    error,
    runLayout,
  };
}
