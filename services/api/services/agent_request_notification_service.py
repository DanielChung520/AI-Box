# 代碼功能說明: Agent 申請通知服務
# 創建日期: 2026-01-17 18:48 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 18:48 UTC+8

"""Agent 申請通知服務 - 提供郵件和系統通知功能"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


class AgentRequestNotificationService:
    """Agent 申請通知服務"""

    def __init__(self):
        """初始化通知服務"""
        # 郵件配置（從環境變數讀取）
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@ai-box.internal")
        self.smtp_from_name = os.getenv("SMTP_FROM_NAME", "AI-Box System")

        # 系統管理員郵箱列表
        self.admin_emails = os.getenv("SYSTEM_ADMIN_EMAILS", "").split(",")
        self.admin_emails = [email.strip() for email in self.admin_emails if email.strip()]

        # 郵件模板基礎 URL
        self.base_url = os.getenv("BASE_URL", "http://localhost:3000")

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        發送郵件

        Args:
            to_email: 收件人郵箱
            subject: 郵件主題
            html_content: HTML 格式內容
            text_content: 純文本格式內容（可選）

        Returns:
            是否發送成功
        """
        # 如果未配置 SMTP，記錄警告並返回
        if not self.smtp_username or not self.smtp_password:
            logger.warning(
                f"SMTP not configured, skipping email notification: to={to_email}, subject={subject}"
            )
            return False

        try:
            # 創建郵件
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.smtp_from_name} <{self.smtp_from_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            # 添加純文本版本
            if text_content:
                part1 = MIMEText(text_content, "plain", "utf-8")
                msg.attach(part1)

            # 添加 HTML 版本
            part2 = MIMEText(html_content, "html", "utf-8")
            msg.attach(part2)

            # 發送郵件
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully: to={to_email}, subject={subject}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to send email: to={to_email}, subject={subject}, error={str(e)}",
                exc_info=True,
            )
            return False

    def notify_new_request(
        self,
        request_id: str,
        agent_name: str,
        applicant_name: str,
        applicant_email: str,
    ) -> bool:
        """
        通知系統管理員有新的 Agent 申請

        Args:
            request_id: 申請 ID
            agent_name: Agent 名稱
            applicant_name: 申請人姓名
            applicant_email: 申請人郵箱

        Returns:
            是否通知成功
        """
        if not self.admin_emails:
            logger.warning("No admin emails configured, skipping new request notification")
            return False

        subject = f"[AI-Box] 新的 Agent 申請 - {agent_name}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #667eea; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }}
                .info-box {{ background: white; padding: 15px; margin: 15px 0; border-radius: 6px; border-left: 4px solid #667eea; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 6px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🔔 新的 Agent 申請</h2>
                </div>
                <div class="content">
                    <p>您好，系統管理員！</p>
                    <p>收到一個新的 Agent 註冊申請，請盡快審查：</p>

                    <div class="info-box">
                        <p><strong>申請 ID:</strong> {request_id}</p>
                        <p><strong>Agent 名稱:</strong> {agent_name}</p>
                        <p><strong>申請人:</strong> {applicant_name}</p>
                        <p><strong>聯繫郵箱:</strong> {applicant_email}</p>
                    </div>

                    <a href="{self.base_url}/#/admin/agent-requests" class="button">查看申請詳情</a>

                    <p style="margin-top: 20px; font-size: 12px; color: #666;">
                        此郵件由 AI-Box 系統自動發送，請勿直接回覆。
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        新的 Agent 申請

        申請 ID: {request_id}
        Agent 名稱: {agent_name}
        申請人: {applicant_name}
        聯繫郵箱: {applicant_email}

        請訪問 {self.base_url}/#/admin/agent-requests 查看申請詳情。

        此郵件由 AI-Box 系統自動發送，請勿直接回覆。
        """

        # 發送給所有系統管理員
        success = True
        for admin_email in self.admin_emails:
            if not self._send_email(admin_email, subject, html_content, text_content):
                success = False

        return success

    def notify_request_approved(
        self,
        request_id: str,
        agent_name: str,
        applicant_email: str,
        secret_id: str,
    ) -> bool:
        """
        通知申請者申請已批准

        Args:
            request_id: 申請 ID
            agent_name: Agent 名稱
            applicant_email: 申請人郵箱
            secret_id: Secret ID

        Returns:
            是否通知成功
        """
        subject = f"[AI-Box] Agent 申請已批准 - {agent_name}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #28a745; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }}
                .info-box {{ background: white; padding: 15px; margin: 15px 0; border-radius: 6px; border-left: 4px solid #28a745; }}
                .warning-box {{ background: #fff3cd; padding: 15px; margin: 15px 0; border-radius: 6px; border-left: 4px solid #ffc107; }}
                .code {{ background: #f1f3f5; padding: 10px; border-radius: 4px; font-family: monospace; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>✅ Agent 申請已批准</h2>
                </div>
                <div class="content">
                    <p>恭喜！您的 Agent 註冊申請已經通過審核。</p>

                    <div class="info-box">
                        <p><strong>申請 ID:</strong> {request_id}</p>
                        <p><strong>Agent 名稱:</strong> {agent_name}</p>
                        <p><strong>Secret ID:</strong></p>
                        <div class="code">{secret_id}</div>
                    </div>

                    <div class="warning-box">
                        <p><strong>⚠️ 重要提示：</strong></p>
                        <p>1. Secret Key 已通過系統界面顯示，僅顯示一次，請妥善保管</p>
                        <p>2. Secret ID 和 Secret Key 用於 Agent 認證，請勿洩露給他人</p>
                        <p>3. 如果遺失 Secret Key，請重新申請</p>
                    </div>

                    <p><strong>接下來的步驟：</strong></p>
                    <ol>
                        <li>配置您的 Agent 使用分配的 Secret ID 和 Secret Key</li>
                        <li>測試 Agent 連接是否正常</li>
                        <li>查看 <a href="{self.base_url}/#/docs/agent-integration">Agent 集成文檔</a> 了解更多</li>
                    </ol>

                    <p style="margin-top: 20px; font-size: 12px; color: #666;">
                        此郵件由 AI-Box 系統自動發送，請勿直接回覆。
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Agent 申請已批准

        恭喜！您的 Agent 註冊申請已經通過審核。

        申請 ID: {request_id}
        Agent 名稱: {agent_name}
        Secret ID: {secret_id}

        重要提示：
        - Secret Key 已通過系統界面顯示，僅顯示一次，請妥善保管
        - Secret ID 和 Secret Key 用於 Agent 認證，請勿洩露給他人
        - 如果遺失 Secret Key，請重新申請

        接下來的步驟：
        1. 配置您的 Agent 使用分配的 Secret ID 和 Secret Key
        2. 測試 Agent 連接是否正常
        3. 查看 Agent 集成文檔了解更多: {self.base_url}/#/docs/agent-integration

        此郵件由 AI-Box 系統自動發送，請勿直接回覆。
        """

        return self._send_email(applicant_email, subject, html_content, text_content)

    def notify_request_rejected(
        self,
        request_id: str,
        agent_name: str,
        applicant_email: str,
        rejection_reason: str,
    ) -> bool:
        """
        通知申請者申請已拒絕

        Args:
            request_id: 申請 ID
            agent_name: Agent 名稱
            applicant_email: 申請人郵箱
            rejection_reason: 拒絕原因

        Returns:
            是否通知成功
        """
        subject = f"[AI-Box] Agent 申請已拒絕 - {agent_name}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #dc3545; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }}
                .info-box {{ background: white; padding: 15px; margin: 15px 0; border-radius: 6px; border-left: 4px solid #dc3545; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 6px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>❌ Agent 申請已拒絕</h2>
                </div>
                <div class="content">
                    <p>很抱歉，您的 Agent 註冊申請未能通過審核。</p>

                    <div class="info-box">
                        <p><strong>申請 ID:</strong> {request_id}</p>
                        <p><strong>Agent 名稱:</strong> {agent_name}</p>
                        <p><strong>拒絕原因:</strong></p>
                        <p>{rejection_reason}</p>
                    </div>

                    <p>如果您對拒絕原因有疑問，或希望修改申請後重新提交，請聯繫系統管理員。</p>

                    <a href="{self.base_url}/#/agent-registration" class="button">重新申請</a>

                    <p style="margin-top: 20px; font-size: 12px; color: #666;">
                        此郵件由 AI-Box 系統自動發送，請勿直接回覆。
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Agent 申請已拒絕

        很抱歉，您的 Agent 註冊申請未能通過審核。

        申請 ID: {request_id}
        Agent 名稱: {agent_name}
        拒絕原因: {rejection_reason}

        如果您對拒絕原因有疑問，或希望修改申請後重新提交，請聯繫系統管理員。

        重新申請: {self.base_url}/#/agent-registration

        此郵件由 AI-Box 系統自動發送，請勿直接回覆。
        """

        return self._send_email(applicant_email, subject, html_content, text_content)

    def notify_request_revoked(
        self,
        request_id: str,
        agent_name: str,
        applicant_email: str,
        revoke_reason: str,
    ) -> bool:
        """
        通知申請者申請已撤銷

        Args:
            request_id: 申請 ID
            agent_name: Agent 名稱
            applicant_email: 申請人郵箱
            revoke_reason: 撤銷原因

        Returns:
            是否通知成功
        """
        subject = f"[AI-Box] Agent 申請已撤銷 - {agent_name}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #6c757d; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }}
                .info-box {{ background: white; padding: 15px; margin: 15px 0; border-radius: 6px; border-left: 4px solid #6c757d; }}
                .warning-box {{ background: #fff3cd; padding: 15px; margin: 15px 0; border-radius: 6px; border-left: 4px solid #ffc107; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>⚫ Agent 申請已撤銷</h2>
                </div>
                <div class="content">
                    <p>您的 Agent 註冊申請已被系統管理員撤銷。</p>

                    <div class="info-box">
                        <p><strong>申請 ID:</strong> {request_id}</p>
                        <p><strong>Agent 名稱:</strong> {agent_name}</p>
                        <p><strong>撤銷原因:</strong></p>
                        <p>{revoke_reason}</p>
                    </div>

                    <div class="warning-box">
                        <p><strong>⚠️ 重要提示：</strong></p>
                        <p>1. 原有的 Secret ID 和 Secret Key 已失效，無法再使用</p>
                        <p>2. 如需繼續使用 Agent，請重新申請</p>
                    </div>

                    <p>如果您對撤銷原因有疑問，請聯繫系統管理員。</p>

                    <p style="margin-top: 20px; font-size: 12px; color: #666;">
                        此郵件由 AI-Box 系統自動發送，請勿直接回覆。
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Agent 申請已撤銷

        您的 Agent 註冊申請已被系統管理員撤銷。

        申請 ID: {request_id}
        Agent 名稱: {agent_name}
        撤銷原因: {revoke_reason}

        重要提示：
        - 原有的 Secret ID 和 Secret Key 已失效，無法再使用
        - 如需繼續使用 Agent，請重新申請

        如果您對撤銷原因有疑問，請聯繫系統管理員。

        此郵件由 AI-Box 系統自動發送，請勿直接回覆。
        """

        return self._send_email(applicant_email, subject, html_content, text_content)


# 單例服務
_notification_service: Optional[AgentRequestNotificationService] = None


def get_agent_request_notification_service() -> AgentRequestNotificationService:
    """獲取 Agent 申請通知服務單例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = AgentRequestNotificationService()
    return _notification_service
