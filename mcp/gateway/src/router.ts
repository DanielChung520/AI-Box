/**
 * 路由引擎
 *
 * 创建日期: 2025-12-31
 * 创建人: Daniel Chung
 * 最后修改日期: 2025-12-31
 */

export class Router {
  private routes: Map<string, string> = new Map();

  constructor(private env: any) {
    this.loadRoutes();
  }

  private loadRoutes() {
    // 从环境变量加载路由配置
    if (this.env.MCP_ROUTES) {
      try {
        const routesConfig = JSON.parse(this.env.MCP_ROUTES);
        for (const route of routesConfig) {
          this.routes.set(route.pattern, route.target);
        }
      } catch (error) {
        console.error('Failed to parse MCP_ROUTES:', error);
      }
    }
  }

  async route(mcpRequest: any): Promise<string | null> {
    // 从请求中提取工具名称
    const toolName = mcpRequest.params?.name;
    if (!toolName) {
      return null;
    }

    // 匹配路由规则
    for (const [pattern, target] of this.routes.entries()) {
      if (this.matchPattern(pattern, toolName)) {
        return target;
      }
    }

    // 默认路由（如果配置了）
    return this.env.DEFAULT_MCP_ENDPOINT || null;
  }

  private matchPattern(pattern: string, toolName: string): boolean {
    // 支持通配符匹配
    // 例如: "finance_*" 匹配 "finance_quote", "finance_history" 等
    const regex = new RegExp('^' + pattern.replace(/\*/g, '.*') + '$');
    return regex.test(toolName);
  }
}
