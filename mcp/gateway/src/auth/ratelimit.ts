/**
 * 速率限制器
 *
 * 创建日期: 2025-12-31
 * 创建人: Daniel Chung
 * 最后修改日期: 2025-12-31
 */

export class RateLimiter {
  constructor(private env: any) {}

  async checkRateLimit(
    userId: string,
    toolName: string
  ): Promise<{ allowed: boolean; remaining: number }> {
    // 1. 获取速率限制配置
    const limit = await this.getRateLimit(userId, toolName);

    // 2. 构建速率限制键
    const key = `ratelimit:${userId}:${toolName}`;

    // 3. 获取当前计数
    const countStr = await this.env.RATE_LIMIT_STORE.get(key);
    const count = countStr ? parseInt(countStr, 10) : 0;

    // 4. 检查是否超过限制
    if (count >= limit) {
      return { allowed: false, remaining: 0 };
    }

    // 5. 增加计数（TTL: 60 秒）
    await this.env.RATE_LIMIT_STORE.put(key, String(count + 1), {
      expirationTtl: 60,
    });

    return { allowed: true, remaining: limit - count - 1 };
  }

  private async getRateLimit(userId: string, toolName: string): Promise<number> {
    // 1. 尝试获取用户特定的速率限制配置
    const userConfig = await this.env.PERMISSIONS_STORE.get(
      `permissions:${userId}`,
      'json'
    );

    if (userConfig?.rate_limits) {
      // 检查工具特定的速率限制
      for (const [pattern, limit] of Object.entries(userConfig.rate_limits)) {
        if (this.matchPattern(pattern, toolName)) {
          return limit as number;
        }
      }
      // 返回默认速率限制
      return (userConfig.rate_limits.default as number) || 100;
    }

    // 2. 返回全局默认速率限制
    return parseInt(this.env.DEFAULT_RATE_LIMIT || '100', 10);
  }

  private matchPattern(pattern: string, toolName: string): boolean {
    const regex = new RegExp('^' + pattern.replace(/\*/g, '.*') + '$');
    return regex.test(toolName);
  }
}
