/**
 * 请求/响应过滤器
 *
 * 创建日期: 2025-12-31
 * 创建人: Daniel Chung
 * 最后修改日期: 2025-12-31
 */

export class RequestFilter {
  constructor(private env: any) {}

  async filter(request: Request, mcpRequest: any): Promise<any> {
    // 1. 创建过滤后的请求副本
    const filtered = { ...mcpRequest };

    // 2. 数据脱敏（如果需要）
    if (this.env.ENABLE_DATA_MASKING === 'true') {
      filtered.params = this.maskSensitiveData(filtered.params);
    }

    return filtered;
  }

  async filterResponse(response: any): Promise<any> {
    // 响应过滤逻辑
    // 可以在这里移除敏感信息、格式化响应等
    const filtered = { ...response };

    // 如果需要，可以过滤响应中的敏感数据
    if (this.env.ENABLE_RESPONSE_FILTERING === 'true') {
      // 实现响应过滤逻辑
    }

    return filtered;
  }

  private maskSensitiveData(data: any): any {
    // 实现数据脱敏逻辑
    // 例如：移除 PII、敏感字段等

    if (typeof data !== 'object' || data === null) {
      return data;
    }

    const sensitiveFields = ['password', 'api_key', 'token', 'secret', 'ssn', 'credit_card'];
    const masked = { ...data };

    for (const key in masked) {
      if (sensitiveFields.some((field) => key.toLowerCase().includes(field))) {
        masked[key] = '***MASKED***';
      } else if (typeof masked[key] === 'object') {
        masked[key] = this.maskSensitiveData(masked[key]);
      }
    }

    return masked;
  }
}
