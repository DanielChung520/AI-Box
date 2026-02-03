#!/usr/bin/env python3
"""
Data-Agent Intent RAG 視覺化工具

功能：
1. 顯示意圖模板的分類圖譜
2. 視覺化查詢相似度
3. 展示表關係圖

使用方式：
    python data_agent_intent_rag_viz.py
    python data_agent_intent_rag_viz.py --query "計算各倉庫的總庫存量"
    python data_agent_intent_rag_viz.py --graph
"""

import json
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from data_agent_intent_rag import query_rag, INTENT_TEMPLATES, get_embedding

plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial Unicode MS", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def build_intent_graph():
    """構建意圖關係圖"""
    G = nx.Graph()

    # 定義類別顏色
    colors = {
        "query_inventory": "#FF6B6B",  # 紅 - 庫存查詢
        "statistics": "#4ECDC4",  # 青 - 統計
        "calculate_count": "#45B7D1",  # 藍 - 計數
        "query_item": "#96CEB4",  # 綠 - 料件
        "query_order": "#FFEAA7",  # 黃 - 訂單
        "query_price": "#DDA0DD",  # 紫 - 價格
        "query_transaction": "#F39C12",  # 橙 - 交易
    }

    # 添加節點
    for template in INTENT_TEMPLATES:
        query_type = template.get("type", "unknown")
        G.add_node(
            template["id"],
            label=template["query"][:20] + "..."
            if len(template["query"]) > 20
            else template["query"],
            query=template["query"],
            sql=template["sql"],
            type=query_type,
            color=colors.get(query_type, "#CCCCCC"),
        )

    # 添加邊（根據 SQL 中的表關聯）
    table_groups = defaultdict(list)
    for template in INTENT_TEMPLATES:
        sql = template["sql"].upper()
        if "IMG_FILE" in sql:
            table_groups["img_file"].append(template["id"])
        elif "TLF_FILE" in sql:
            table_groups["tlf_file"].append(template["id"])
        elif "IMA_FILE" in sql:
            table_groups["ima_file"].append(template["id"])
        elif "PRTC_FILE" in sql or "PRIC" in sql:
            table_groups["prc_file"].append(template["id"])
        elif "COPTC_FILE" in sql:
            table_groups["coptc_file"].append(template["id"])

    # 添加同表關聯邊
    for table, ids in table_groups.items():
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                G.add_edge(ids[i], ids[j], relation="same_table")

    return G, colors, table_groups


def visualize_intent_graph(
    G: nx.Graph, colors: Dict, table_groups: Dict, save_path: Optional[str] = None
):
    """視覺化意圖關係圖"""
    fig, ax = plt.subplots(1, 1, figsize=(20, 16))

    # 計算佈局
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    # 按類別分組節點
    type_nodes = defaultdict(list)
    for node in G.nodes():
        node_type = G.nodes[node].get("type", "unknown")
        type_nodes[node_type].append(node)

    # 繪製邊
    nx.draw_networkx_edges(G, pos, alpha=0.2, edge_color="gray", ax=ax)

    # 按類別繪製節點
    for node_type, nodes in type_nodes.items():
        node_colors = [colors.get(node_type, "#CCCCCC") for node in nodes]
        nx.draw_networkx_nodes(
            G, pos, nodelist=nodes, node_color=node_colors, node_size=500, alpha=0.8, ax=ax
        )

    # 添加標籤（只顯示 ID）
    labels = {node: G.nodes[node].get("id", node) for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=6, ax=ax)

    # 圖例
    legend_patches = [
        mpatches.Patch(color=color, label=type_name) for type_name, color in colors.items()
    ]
    ax.legend(handles=legend_patches, loc="upper left", fontsize=8)

    # 表關係標籤
    table_labels = {node: "" for node in G.nodes()}
    for table, ids in table_groups.items():
        for id in ids:
            if id in table_labels:
                table_labels[id] = table

    ax.set_title("Data-Agent Intent Template Graph\n(按表關係分組，顏色按意圖類型)", fontsize=14)
    ax.axis("off")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"圖譜已保存: {save_path}")

    return fig


def visualize_query_search(query: str, top_k: int = 5, save_path: Optional[str] = None):
    """視覺化查詢搜尋結果"""
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    # 左側：相似度分布
    ax1 = axes[0]

    # 獲取所有相似度
    embeddings = [get_embedding(t["query"]) for t in INTENT_TEMPLATES]
    query_emb = get_embedding(query)

    # 計算相似度
    similarities = []
    for i, emb in enumerate(embeddings):
        sim = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb))
        similarities.append((INTENT_TEMPLATES[i], sim))

    # 排序
    similarities.sort(key=lambda x: x[1], reverse=True)

    # 繪製 top_k 條形圖
    top_k_data = similarities[:top_k]
    labels = [
        d[0]["query"][:25] + "..." if len(d[0]["query"]) > 25 else d[0]["query"] for d in top_k_data
    ]
    values = [d[1] for d in top_k_data]
    colors_bar = ["#FF6B6B" if v > 0.8 else "#4ECDC4" if v > 0.7 else "#45B7D1" for v in values]

    bars = ax1.barh(range(len(labels)), values, color=colors_bar)
    ax1.set_yticks(range(len(labels)))
    ax1.set_yticklabels(labels, fontsize=8)
    ax1.invert_yaxis()
    ax1.set_xlabel("Similarity Score")
    ax1.set_title(f'Top {top_k} Similar Intent Templates\nQuery: "{query[:30]}..."')
    ax1.set_xlim(0, 1)

    # 添加數值標籤
    for i, (bar, val) in enumerate(zip(bars, values)):
        ax1.text(val + 0.01, i, f"{val:.4f}", va="center", fontsize=8)

    # 右側：查詢結果詳情
    ax2 = axes[1]
    ax2.axis("off")

    result_text = f"Query: {query}\n\n"
    result_text += "=" * 60 + "\n"
    result_text += f"Top {top_k} Results:\n\n"

    for i, (template, sim) in enumerate(top_k_data, 1):
        result_text += f"{i}. [{template['type']}] {template['query']}\n"
        result_text += f"   Similarity: {sim:.4f}\n"
        result_text += f"   SQL: {template['sql']}\n"
        result_text += "-" * 40 + "\n"

    ax2.text(
        0.05,
        0.95,
        result_text,
        transform=ax2.transAxes,
        fontsize=8,
        verticalalignment="top",
        fontfamily="monospace",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"查詢結果圖已保存: {save_path}")

    return fig


def visualize_table_relationship(table_groups: Dict, save_path: Optional[str] = None):
    """視覺化表關係圖"""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    G = nx.Graph()

    # 添加表節點
    for table in table_groups.keys():
        G.add_node(table, type="table")

    # 添加表間關係（如果有共享的模板，則表示可能關聯）
    tables = list(table_groups.keys())
    for i in range(len(tables)):
        for j in range(i + 1, len(tables)):
            # 計算共同模板數量
            common = set(table_groups[tables[i]]) & set(table_groups[tables[j]])
            if common:
                G.add_edge(tables[i], tables[j], weight=len(common))

    # 佈局
    pos = nx.spring_layout(G, k=3, iterations=50, seed=42)

    # 繪製節點
    table_colors = {
        "img_file": "#FF6B6B",
        "tlf_file": "#4ECDC4",
        "ima_file": "#45B7D1",
        "prc_file": "#96CEB4",
        "coptc_file": "#FFEAA7",
    }

    node_colors = [table_colors.get(node, "#CCCCCC") for node in G.nodes()]
    node_sizes = [1000 + len(table_groups.get(node, [])) * 100 for node in G.nodes()]

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.8, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=10, ax=ax)

    # 繪製邊（寬度表示關聯強度）
    edges = G.edges(data=True)
    if edges:
        edge_widths = [d.get("weight", 1) for u, v, d in edges]
        nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.5, ax=ax)

    # 添加模板數量標籤
    for node in G.nodes():
        count = len(table_groups.get(node, []))
        ax.annotate(
            f"{count} templates",
            xy=pos[node],
            xytext=(10, 10),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_title(
        "Database Table Relationship Graph\n(Node size = number of templates)", fontsize=14
    )
    ax.axis("off")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"表關係圖已保存: {save_path}")

    return fig


def main():
    parser = argparse.ArgumentParser(description="Data-Agent Intent RAG Visualization")
    parser.add_argument("--query", "-q", type=str, help="Query to visualize")
    parser.add_argument("--graph", "-g", action="store_true", help="Generate intent graph")
    parser.add_argument(
        "--tables", "-t", action="store_true", help="Generate table relationship graph"
    )
    parser.add_argument("--output", "-o", type=str, help="Output image path")

    args = parser.parse_args()

    output_dir = Path(__file__).parent / ".." / ".." / ".ds-docs" / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.graph:
        print("生成意圖關係圖...")
        G, colors, table_groups = build_intent_graph()
        save_path = args.output or str(output_dir / "data_agent_intent_graph.png")
        visualize_intent_graph(G, colors, table_groups, save_path)
        plt.show()

    elif args.query:
        print(f"分析查詢: {args.query}")
        save_path = args.output or str(output_dir / f"query_{args.query[:20]}.png")
        visualize_query_search(args.query, save_path=save_path)
        plt.show()

    elif args.tables:
        print("生成表關係圖...")
        _, _, table_groups = build_intent_graph()
        save_path = args.output or str(output_dir / "table_relationship_graph.png")
        visualize_table_relationship(table_groups, save_path)
        plt.show()

    else:
        # 預設：生成所有圖表
        print("生成所有圖表...")

        G, colors, table_groups = build_intent_graph()

        # 意圖圖譜
        visualize_intent_graph(
            G, colors, table_groups, str(output_dir / "data_agent_intent_graph.png")
        )

        # 表關係圖
        visualize_table_relationship(table_groups, str(output_dir / "table_relationship_graph.png"))

        # 示例查詢
        visualize_query_search(
            "計算各倉庫的總庫存量", save_path=str(output_dir / "query_example.png")
        )

        print(f"\n所有圖表已保存到: {output_dir}")
        print("\n生成以下圖表:")
        print("  1. data_agent_intent_graph.png - 意圖模板關係圖")
        print("  2. table_relationship_graph.png - 資料表關係圖")
        print("  3. query_example.png - 查詢相似度示例")


if __name__ == "__main__":
    main()
