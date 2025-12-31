/**
 * 审计日志记录器
 *
 * 创建日期: 2025-12-31
 * 创建人: Daniel Chung
 * 最后修改日期: 2025-12-31
 */

export class AuditLogger {
  constructor(private env: any) {}

  async log(auditData: any): Promise<void> {
    try {
      // 1. 记录到 Cloudflare Logpush（如果配置）
      if (this.env.LOG_ENDPOINT) {
        await fetch(this.env.LOG_ENDPOINT, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.env.LOG_API_KEY}`,
          },
          body: JSON.stringify(auditData),
        });
      }

      // 2. 记录到 R2 存储（如果配置）
      if (this.env.AUDIT_BUCKET) {
        const logKey = `audit/${new Date().toISOString().split('T')[0]}/${auditData.requestId}.json`;
        await this.env.AUDIT_BUCKET.put(logKey, JSON.stringify(auditData));
      }

      // 3. 记录到 Durable Object（如果配置）
      if (this.env.AUDIT_LOG) {
        const id = this.env.AUDIT_LOG.idFromName('audit-log');
        const stub = this.env.AUDIT_LOG.get(id);
        await stub.fetch('http://internal/log', {
          method: 'POST',
          body: JSON.stringify(auditData),
        });
      }

      // 4. 记录到控制台（开发环境）
      console.log('Audit log:', JSON.stringify(auditData));
    } catch (error) {
      console.error('Failed to log audit:', error);
      // 不抛出错误，避免影响主流程
    }
  }

  async logError(errorData: any): Promise<void> {
    await this.log({
      ...errorData,
      type: 'error',
    });
  }
}
