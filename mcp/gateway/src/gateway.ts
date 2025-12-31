/**
 * MCP Gateway 核心实现
 *
 * 创建日期: 2025-12-31
 * 创建人: Daniel Chung
 * 最后修改日期: 2025-12-31
 */

import { Router } from './router';
import { AuthManager } from './auth';
import { RequestFilter } from './filter';
import { AuditLogger } from './audit';
import { PermissionManager } from './auth/permissions';
import { RateLimiter } from './auth/ratelimit';

export class MCPGateway {
  private router: Router;
  private authManager: AuthManager;
  private permissionManager: PermissionManager;
  private rateLimiter: RateLimiter;
  private requestFilter: RequestFilter;
  private auditLogger: AuditLogger;

  constructor(private env: any) {
    this.router = new Router(env);
    this.authManager = new AuthManager(env);
    this.permissionManager = new PermissionManager(env);
    this.rateLimiter = new RateLimiter(env);
    this.requestFilter = new RequestFilter(env);
    this.auditLogger = new AuditLogger(env);
  }

  async handle(request: Request, ctx: ExecutionContext): Promise<Response> {
    const startTime = Date.now();
    const requestId = crypto.randomUUID();
    let body: any = null;

    // 处理非 POST 请求
    if (request.method !== 'POST') {
      return new Response(
        JSON.stringify({
          jsonrpc: '2.0',
          id: null,
          error: {
            code: -32600,
            message: 'Invalid Request: Only POST method is supported',
            data: { method: request.method },
          },
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    try {
      // 1. 解析请求
      try {
        body = await request.json();
      } catch (parseError) {
        return this.errorResponse(
          null,
          -32700,
          'Parse error: Invalid JSON',
          { error: String(parseError) }
        );
      }

      if (!body) {
        return this.errorResponse(
          null,
          -32600,
          'Invalid Request: Request body is empty'
        );
      }

      const mcpRequest = body;

      // 2. Layer 1: 验证 Gateway Secret
      if (this.env.GATEWAY_SECRET) {
        const authHeader = request.headers.get('X-Gateway-Secret');
        if (authHeader !== this.env.GATEWAY_SECRET) {
          return this.errorResponse(mcpRequest.id, -32001, 'Unauthorized: Invalid Gateway Secret');
        }
      }

      // 3. 提取用户信息
      const userId = request.headers.get('X-User-ID') || 'anonymous';
      const tenantId = request.headers.get('X-Tenant-ID') || 'default';
      const toolName = request.headers.get('X-Tool-Name') || mcpRequest.params?.name;

      if (!toolName) {
        return this.errorResponse(mcpRequest.id, -32602, 'Invalid params: tool name is required');
      }

      // 4. Layer 2: 检查用户权限
      const hasPermission = await this.permissionManager.checkPermission(
        userId,
        tenantId,
        toolName
      );
      if (!hasPermission) {
        return this.errorResponse(mcpRequest.id, -32001, 'Unauthorized: No permission');
      }

      // 5. Layer 2: 检查速率限制
      const rateLimitResult = await this.rateLimiter.checkRateLimit(userId, toolName);
      if (!rateLimitResult.allowed) {
        return this.errorResponse(
          mcpRequest.id,
          -32002,
          'Rate limit exceeded',
          { remaining: rateLimitResult.remaining }
        );
      }

      // 6. 路由到目标 MCP Server
      const targetEndpoint = await this.router.route(mcpRequest);
      if (!targetEndpoint) {
        return this.errorResponse(mcpRequest.id, -32601, 'Method not found: No route for tool');
      }

      // 7. Layer 3: 获取外部 MCP 认证信息
      const authResult = await this.authManager.authenticate(toolName);
      if (!authResult.authorized) {
        return this.errorResponse(mcpRequest.id, -32001, 'Unauthorized: Failed to authenticate with MCP server');
      }

      // 8. 请求过滤（移除敏感信息）
      const filteredRequest = await this.requestFilter.filter(request, mcpRequest);

      // 9. 转发请求到外部 MCP Server
      const response = await this.forwardRequest(
        targetEndpoint,
        filteredRequest,
        authResult.headers
      );

      // 10. 响应过滤
      const filteredResponse = await this.requestFilter.filterResponse(response);

      // 11. 审计日志（异步，不阻塞响应）
      ctx.waitUntil(
        this.auditLogger.log({
          requestId,
          timestamp: new Date().toISOString(),
          userId,
          tenantId,
          method: mcpRequest.method,
          toolName,
          targetEndpoint,
          request: filteredRequest,
          response: filteredResponse,
          latency: Date.now() - startTime,
        })
      );

      return new Response(JSON.stringify(filteredResponse), {
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (error) {
      // 记录错误
      ctx.waitUntil(
        this.auditLogger.logError({
          requestId,
          error: String(error),
          timestamp: new Date().toISOString(),
        })
      );

      // 尝试从 body 获取 id，如果 body 未定义则使用 null
      const errorId = body?.id ?? null;
      return this.errorResponse(
        errorId,
        -32603,
        'Internal error',
        { error: String(error) }
      );
    }
  }

  private async forwardRequest(
    endpoint: string,
    request: any,
    authHeaders: Record<string, string>
  ): Promise<any> {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
        // 移除追踪信息，隐藏真实 IP
        'X-Forwarded-For': 'Cloudflare-IP',
        'X-Request-Source': 'AI-Box-Gateway',
        // 移除可能泄露信息的请求头
        'User-Agent': 'AI-Box-MCP-Gateway/1.0',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  }

  private errorResponse(
    id: any,
    code: number,
    message: string,
    data?: any
  ): Response {
    return new Response(
      JSON.stringify({
        jsonrpc: '2.0',
        id,
        error: { code, message, data },
      }),
      {
        status: 200, // JSON-RPC 错误仍返回 200
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
