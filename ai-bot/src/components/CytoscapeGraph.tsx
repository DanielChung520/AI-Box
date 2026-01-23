/**
 * 代碼功能說明: Cytoscape.js 圖譜可視化組件 - 修復版
 * 創建日期: 2026-01-23
 */

import { useEffect, useRef, useCallback } from 'react';

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

interface CytoscapeGraphProps {
  nodes: NodeData[];
  edges: EdgeData[];
  height?: number;
  layoutType: 'force' | 'circular' | 'grid';
  isDarkMode: boolean;
  onNodeClick?: (nodeId: string) => void;
  onEdgeClick?: (edgeData: { source: string; target: string; label: string }) => void;
  onNodeHover?: (nodeData: NodeData | null) => void;
}

const ENTITY_TYPE_COLORS: Record<string, string> = {
  'Person': '#4A90E2', 'Organization': '#50C878', 'Location': '#FF6B6B',
  'Event': '#FFA500', 'Document': '#9B59B6', 'Software': '#3498DB',
  'Task': '#E74C3C', 'Command': '#1ABC9C', 'Feature': '#F39C12',
  'NotionPage': '#E91E63', 'Notion_Workspace': '#9C27B0', 'Notion_User': '#2196F3',
  'Product': '#00BCD4', 'Service': '#8BC34A', 'Technology': '#FF5722',
  'Company': '#3F51B5', 'Project': '#FF9800', 'Concept': '#9C27B0',
  'Method': '#009688', 'Tool': '#795548', 'Resource': '#607D8B',
  'File': '#6366F1', 'API': '#10B981', 'Database': '#F43F5E',
  'Model': '#8B5CF6', 'Dataset': '#14B8A6', 'Endpoint': '#EC4899',
  'Parameter': '#84CC16', 'Variable': '#06B6D4', 'Function': '#F97316',
  'Class': '#3B82F6', 'Module': '#A855F7', 'Package': '#22D3EE',
  'Version': '#FBBF24', 'User': '#60A5FA', 'Role': '#34D399',
  'Permission': '#F87171', 'Tag': '#A78BFA', 'Category': '#FB923C',
  'Status': '#4ADE80', 'Priority': '#F43F5E', 'Owner': '#818CF8',
  'Creator': '#38BDF8', 'Default': '#94A3B8',
};

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316'];

function getColor(entityType: string, nodeId: string) {
  if (ENTITY_TYPE_COLORS[entityType]) return ENTITY_TYPE_COLORS[entityType];
  let hash = 0;
  for (let i = 0; i < nodeId.length; i++) hash = ((hash << 5) - hash) + nodeId.charCodeAt(i);
  return COLORS[Math.abs(hash) % COLORS.length];
}

export default function CytoscapeGraph({
  nodes, edges, height = 400, layoutType, isDarkMode,
  onNodeClick, onEdgeClick, onNodeHover
}: CytoscapeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);
  const lastNodesRef = useRef<string[]>([]);
  const lastEdgesRef = useRef<string[]>([]);
  const currentNodesRef = useRef<NodeData[]>([]);
  const currentEdgesRef = useRef<EdgeData[]>([]);

  // 保存當前數據
  useEffect(() => {
    currentNodesRef.current = nodes;
    currentEdgesRef.current = edges;
  }, [nodes, edges]);

  const shouldReinit = useCallback(() => {
    const nodeIds = nodes.map(n => n.id);
    const edgeIds = edges.map(e => `${e.source}-${e.target}`);

    const nodeChanged = nodeIds.length !== lastNodesRef.current.length ||
      nodeIds.some((id, i) => id !== lastNodesRef.current[i]);
    const edgeChanged = edgeIds.length !== lastEdgesRef.current.length ||
      edgeIds.some((id, i) => id !== lastEdgesRef.current[i]);

    lastNodesRef.current = nodeIds;
    lastEdgesRef.current = edgeIds;

    return nodeChanged || edgeChanged;
  }, [nodes, edges]);

  const doLayout = useCallback((type: string) => {
    if (!cyRef.current) return;

    const config: any = {
      name: type === 'force' ? 'cose' : type === 'circular' ? 'circle' : 'grid',
      animate: true,
      animationDuration: 800,
      easing: 'ease-in-out',
    };

    if (type === 'force') {
      config.nodeRepulsion = 4500;
      config.idealEdgeLength = 120;
      config.numIter = 1000;
    } else if (type === 'circular') {
      config.radius = Math.min(height / 2 - 60, 250);
    } else {
      const sqrt = Math.ceil(Math.sqrt(nodes.length));
      config.rows = sqrt;
      config.cols = sqrt;
    }

    cyRef.current.layout(config).run();
  }, [nodes.length, height]);

  // 監控數據變化
  useEffect(() => {
    const initGraph = async () => {
      if (!containerRef.current) return;

      const Cytoscape = (await import('cytoscape')).default;

      if (cyRef.current) {
        try { cyRef.current.destroy(); } catch {}
        cyRef.current = null;
      }

      const nodeElements = nodes.map((n, i) => ({
        group: 'nodes' as const,
        data: { id: n.id, nodeIndex: i + 1, entityType: n.entityType, label: n.originalLabel },
        style: { 'background-color': getColor(n.entityType, n.id), 'border-width': 3, 'border-color': '#fff' }
      }));

      const edgeElements = edges.map((e, i) => ({
        group: 'edges' as const,
        data: { id: e.id || `e${i}`, source: e.source, target: e.target, label: e.label }
      }));

      const cy = Cytoscape({
        container: containerRef.current,
        elements: [...nodeElements, ...edgeElements] as any,
        style: [
          { selector: 'node', style: { 'width': 36, 'height': 36, 'shape': 'ellipse', 'label': 'data(nodeIndex)', 'color': '#000', 'font-size': '12px', 'font-weight': 'bold', 'text-valign': 'bottom', 'text-halign': 'center', 'text-margin-y': 5 } },
          { selector: 'node:selected', style: { 'border-width': 4, 'border-color': '#60a5fa', 'width': 42, 'height': 42 } },
          { selector: 'edge', style: { 'width': 2, 'label': 'data(label)', 'font-size': '10px', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'line-color': '#999', 'target-arrow-color': '#999', 'color': '#666' } },
          { selector: 'edge:selected', style: { 'line-color': '#60a5fa', 'width': 4 } }
        ],
        minZoom: 0.1, maxZoom: 5
      });

      cyRef.current = cy;
      lastNodesRef.current = nodes.map(n => n.id);
      lastEdgesRef.current = edges.map(e => `${e.source}-${e.target}`);

      cy.on('tap', 'node', (e: any) => onNodeClick?.(e.target.id()));
      cy.on('tap', 'edge', (e: any) => onEdgeClick?.(e.target.data()));
      cy.on('tap', (e: any) => { if (e.target === cy) onNodeClick?.(''); });
      cy.on('mouseover', 'node', (e: any) => { const nd = nodes.find(n => n.id === e.target.id()); if (nd) onNodeHover?.(nd); });
      cy.on('mouseout', 'node', () => onNodeHover?.(null));

      setTimeout(() => doLayout(layoutType), 100);
    };

    if (shouldReinit()) {
      initGraph();
    }
  }, [nodes.length, edges.length]);

  // 布局切換
  useEffect(() => {
    const timer = setTimeout(() => {
      if (cyRef.current) {
        doLayout(layoutType);
      }
    }, 50);
    return () => clearTimeout(timer);
  }, [layoutType, doLayout]);

  return (
    <div className="relative w-full" style={{ height }}>
      <div ref={containerRef} className="w-full h-full" style={{ background: isDarkMode ? '#0f172a' : '#f8fafc', borderRadius: '0.5rem' }} />
    </div>
  );
}
