/**
 * 权限管理器
 *
 * 创建日期: 2025-12-31
 * 创建人: Daniel Chung
 * 最后修改日期: 2025-12-31
 */

export class PermissionManager {
  constructor(private env: any) {}

  async checkPermission(
    userId: string,
    tenantId: string,
    toolName: string
  ): Promise<boolean> {
    // 1. 从 KV 存储获取用户权限配置
    const userPermissions = await this.env.PERMISSIONS_STORE.get(
      `permissions:${tenantId}:${userId}`,
      'json'
    );

    // 2. 如果没有配置，检查租户默认权限
    if (!userPermissions) {
      const tenantPermissions = await this.env.PERMISSIONS_STORE.get(
        `permissions:${tenantId}:default`,
        'json'
      );
      if (!tenantPermissions) {
        // 如果没有配置，默认拒绝
        return false;
      }
      return this.matchToolPatterns(tenantPermissions.tools || [], toolName);
    }

    // 3. 检查工具权限
    return this.matchToolPatterns(userPermissions.tools || [], toolName);
  }

  private matchToolPatterns(patterns: string[], toolName: string): boolean {
    // 支持通配符匹配
    // 例如: ["finance_*", "office_*"] 匹配 "finance_quote", "office_word" 等
    for (const pattern of patterns) {
      if (this.matchPattern(pattern, toolName)) {
        return true;
      }
    }
    return false;
  }

  private matchPattern(pattern: string, toolName: string): boolean {
    // 支持通配符匹配
    const regex = new RegExp('^' + pattern.replace(/\*/g, '.*') + '$');
    return regex.test(toolName);
  }
}
