/**
 * Cloudflare MCP Gateway Worker
 * 作为 AI-Box 与外部 MCP Server 之间的隔离层
 *
 * 创建日期: 2025-12-31
 * 创建人: Daniel Chung
 * 最后修改日期: 2025-12-31
 */

import { MCPGateway } from './gateway';

export interface Env {
  // MCP Server 路由配置
  MCP_ROUTES: string; // JSON 格式的路由配置

  // 认证配置（KV 存储）
  AUTH_STORE: KVNamespace;

  // 权限配置（KV 存储）
  PERMISSIONS_STORE: KVNamespace;

  // 速率限制存储（KV 存储）
  RATE_LIMIT_STORE: KVNamespace;

  // 审计日志（Durable Object 或 R2，可选）
  AUDIT_LOG?: DurableObjectNamespace;
  AUDIT_BUCKET?: R2Bucket;

  // 环境变量
  GATEWAY_SECRET: string; // Gateway 密钥（用于验证请求来源）

  // 可选：外部日志服务
  LOG_ENDPOINT?: string;
  LOG_API_KEY?: string;

  // 可选：外部 MCP API Keys（从 Secrets 获取）
  [key: string]: any; // 允许动态访问环境变量
}

export default {
  async fetch(
    request: Request,
    env: Env,
    ctx: ExecutionContext
  ): Promise<Response> {
    try {
      const gateway = new MCPGateway(env);
      return await gateway.handle(request, ctx);
    } catch (error) {
      console.error('Gateway error:', error);
      return new Response(
        JSON.stringify({
          jsonrpc: '2.0',
          id: null,
          error: {
            code: -32603,
            message: 'Internal error',
            data: { error: String(error) },
          },
        }),
        {
          status: 200, // JSON-RPC 错误仍返回 200
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }
  },
};
