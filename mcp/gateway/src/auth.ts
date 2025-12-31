/**
 * 认证授权管理器
 *
 * 创建日期: 2025-12-31
 * 创建人: Daniel Chung
 * 最后修改日期: 2025-12-31
 */

export class AuthManager {
  constructor(private env: any) {}

  async authenticate(
    toolName: string
  ): Promise<{ authorized: boolean; headers: Record<string, string> }> {
    // 1. 从 KV 存储获取认证配置
    const authConfig = await this.env.AUTH_STORE.get(`auth:${toolName}`, 'json');

    if (!authConfig) {
      // 如果没有配置，返回未授权
      return { authorized: false, headers: {} };
    }

    // 2. 根据认证类型构建请求头
    const headers: Record<string, string> = {};

    if (authConfig.type === 'api_key') {
      const apiKey = this.resolveEnvVar(authConfig.api_key);
      const headerName = authConfig.header_name || 'Authorization';
      headers[headerName] =
        authConfig.header_name === 'Authorization' ? `Bearer ${apiKey}` : apiKey;
    } else if (authConfig.type === 'bearer') {
      const token = this.resolveEnvVar(authConfig.token);
      headers['Authorization'] = `Bearer ${token}`;
    } else if (authConfig.type === 'oauth2') {
      // OAuth 2.0 需要获取 access token
      const token = await this.getOAuthToken(authConfig);
      headers['Authorization'] = `Bearer ${token}`;
    } else if (authConfig.type === 'none') {
      // 无认证（公开 API）
      return { authorized: true, headers: {} };
    }

    return { authorized: true, headers };
  }

  private resolveEnvVar(value: string): string {
    if (value.startsWith('${') && value.endsWith('}')) {
      const envVar = value.slice(2, -1);
      // 在 Cloudflare Workers 中，环境变量通过 env 对象访问
      return this.env[envVar] || value;
    }
    return value;
  }

  private async getOAuthToken(config: any): Promise<string> {
    // 实现 OAuth 2.0 Token 获取逻辑
    // 可以使用 Durable Objects 缓存 token
    // 这里简化实现，实际应该：
    // 1. 检查缓存中是否有有效的 token
    // 2. 如果没有或已过期，获取新 token
    // 3. 缓存新 token

    try {
      const response = await fetch(config.token_url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          grant_type: 'client_credentials',
          client_id: this.resolveEnvVar(config.client_id),
          client_secret: this.resolveEnvVar(config.client_secret),
          ...(config.scope ? { scope: config.scope } : {}),
        }),
      });

      if (!response.ok) {
        throw new Error(`OAuth token request failed: ${response.statusText}`);
      }

      const data = await response.json() as { access_token: string };
      return data.access_token;
    } catch (error) {
      console.error('Failed to get OAuth token:', error);
      throw error;
    }
  }
}
