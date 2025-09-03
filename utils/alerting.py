"""
Error Alerting System for DBI Operations Hub
Provides error notification and alerting capabilities.
"""
import os
import json
import traceback
from datetime import datetime
from typing import Dict, List, Optional
from .exceptions import DBIOperationsError
from .logging_config import get_logger

logger = get_logger(__name__)


class AlertSeverity:
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorAlert:
    """Represents an error alert"""
    
    def __init__(self, error: Exception, severity: str = AlertSeverity.MEDIUM, 
                 context: Dict = None, user_id: str = None):
        self.timestamp = datetime.utcnow()
        self.error = error
        self.severity = severity
        self.context = context or {}
        self.user_id = user_id
        self.error_type = type(error).__name__
        self.error_message = str(error)
        self.traceback = traceback.format_exc() if traceback.format_exc().strip() != 'NoneType: None' else None
    
    def to_dict(self) -> Dict:
        """Convert alert to dictionary"""
        alert_data = {
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'context': self.context,
            'user_id': self.user_id,
        }
        
        if self.traceback:
            alert_data['traceback'] = self.traceback
        
        if isinstance(self.error, DBIOperationsError):
            alert_data['error_code'] = self.error.error_code
            alert_data['error_details'] = self.error.details
        
        return alert_data


class AlertManager:
    """Manages error alerts and notifications"""
    
    def __init__(self):
        self.alert_handlers = []
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default alert handlers"""
        # Always add file logging handler
        self.alert_handlers.append(FileAlertHandler())
        
        # Add email handler if configured
        if os.environ.get('ALERT_EMAIL_ENABLED', 'false').lower() == 'true':
            self.alert_handlers.append(EmailAlertHandler())
    
    def send_alert(self, error: Exception, severity: str = AlertSeverity.MEDIUM, 
                   context: Dict = None, user_id: str = None):
        """
        Send an error alert through all configured handlers
        
        Args:
            error: The exception that occurred
            severity: Alert severity level
            context: Additional context information
            user_id: User ID if applicable
        """
        alert = ErrorAlert(error, severity, context, user_id)
        
        logger.error(
            f"Alert triggered: {alert.error_type} - {alert.error_message}",
            extra={
                'severity': severity,
                'error_type': alert.error_type,
                'user_id': user_id,
                'context': context
            }
        )
        
        for handler in self.alert_handlers:
            try:
                handler.handle_alert(alert)
            except Exception as handler_error:
                logger.error(f"Alert handler failed: {handler_error}")
    
    def add_handler(self, handler):
        """Add a custom alert handler"""
        self.alert_handlers.append(handler)


class AlertHandler:
    """Base class for alert handlers"""
    
    def handle_alert(self, alert: ErrorAlert):
        """Handle an alert (to be implemented by subclasses)"""
        raise NotImplementedError


class FileAlertHandler(AlertHandler):
    """Writes alerts to a file"""
    
    def __init__(self, alert_file: str = "logs/alerts.jsonl"):
        self.alert_file = alert_file
        # Ensure directory exists
        os.makedirs(os.path.dirname(alert_file), exist_ok=True)
    
    def handle_alert(self, alert: ErrorAlert):
        """Write alert to file in JSON Lines format"""
        try:
            with open(self.alert_file, 'a') as f:
                f.write(json.dumps(alert.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"Failed to write alert to file: {e}")


class EmailAlertHandler(AlertHandler):
    """Sends alerts via email (placeholder for future implementation)"""
    
    def __init__(self):
        self.smtp_server = os.environ.get('ALERT_SMTP_SERVER')
        self.smtp_port = int(os.environ.get('ALERT_SMTP_PORT', '587'))
        self.smtp_username = os.environ.get('ALERT_SMTP_USERNAME')
        self.smtp_password = os.environ.get('ALERT_SMTP_PASSWORD')
        self.alert_recipients = os.environ.get('ALERT_RECIPIENTS', '').split(',')
        
        # Clean up recipients list
        self.alert_recipients = [email.strip() for email in self.alert_recipients if email.strip()]
    
    def handle_alert(self, alert: ErrorAlert):
        """Send alert via email"""
        # Only send high and critical severity alerts via email
        if alert.severity not in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            return
        
        if not all([self.smtp_server, self.smtp_username, self.smtp_password, self.alert_recipients]):
            logger.warning("Email alerting not properly configured")
            return
        
        # For now, just log that we would send an email
        logger.info(f"Would send email alert to {self.alert_recipients} for {alert.severity} error: {alert.error_message}")
        
        # TODO: Implement actual email sending using smtplib
        # This is a placeholder for future implementation


class WebhookAlertHandler(AlertHandler):
    """Sends alerts to a webhook endpoint"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def handle_alert(self, alert: ErrorAlert):
        """Send alert to webhook"""
        # TODO: Implement webhook sending
        logger.info(f"Would send webhook alert to {self.webhook_url} for {alert.severity} error")


# Global alert manager instance
alert_manager = AlertManager()


def send_error_alert(error: Exception, severity: str = AlertSeverity.MEDIUM, 
                    context: Dict = None, user_id: str = None):
    """
    Convenience function to send an error alert
    
    Args:
        error: The exception that occurred
        severity: Alert severity level
        context: Additional context information  
        user_id: User ID if applicable
    """
    alert_manager.send_alert(error, severity, context, user_id)


def send_critical_alert(error: Exception, context: Dict = None, user_id: str = None):
    """Send a critical severity alert"""
    send_error_alert(error, AlertSeverity.CRITICAL, context, user_id)


def send_high_alert(error: Exception, context: Dict = None, user_id: str = None):
    """Send a high severity alert"""
    send_error_alert(error, AlertSeverity.HIGH, context, user_id)
