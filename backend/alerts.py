import smtplib
import requests
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from collections import defaultdict
from config import config

logger = logging.getLogger("AlertService")

class AlertService:
    """Email & Telegram alerts with retry logic and rate limiting"""
    
    last_alert_time = defaultdict(lambda: None)
    ALERT_THROTTLE_SECONDS = 60  # Minimum 1 min between alerts
    MAX_RETRIES = 3
    
    @staticmethod
    def _should_send_alert(alert_type: str) -> bool:
        """Rate limiting: prevent spam"""
        now = datetime.utcnow()
        last_time = AlertService.last_alert_time.get(alert_type)
        
        if last_time and (now - last_time).total_seconds() < AlertService.ALERT_THROTTLE_SECONDS:
            logger.debug(f"Alert throttled: {alert_type}")
            return False
        
        AlertService.last_alert_time[alert_type] = now
        return True
    
    @staticmethod
    def send_email(subject: str, body: str) -> bool:
        """Send email alert with retry"""
        if not config.SENDER_EMAIL or not config.SENDER_PASSWORD:
            logger.warning("Email not configured")
            return False
        
        if not AlertService._should_send_alert("email"):
            return False
        
        for attempt in range(AlertService.MAX_RETRIES):
            try:
                msg = MIMEMultipart()
                msg["From"] = config.SENDER_EMAIL
                msg["To"] = config.SENDER_EMAIL
                msg["Subject"] = subject
                
                msg.attach(MIMEText(body, "plain"))
                
                with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=10) as server:
                    server.starttls()
                    server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
                    server.send_message(msg)
                
                logger.info(f"Email sent: {subject}")
                return True
            
            except Exception as e:
                logger.warning(f"Email attempt {attempt + 1} failed: {e}")
                if attempt < AlertService.MAX_RETRIES - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"Email failed after {AlertService.MAX_RETRIES} attempts")
        return False
    
    @staticmethod
    def send_telegram(message: str) -> bool:
        """Send Telegram alert with retry"""
        if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
            logger.warning("Telegram not configured")
            return False
        
        if not AlertService._should_send_alert("telegram"):
            return False
        
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        
        for attempt in range(AlertService.MAX_RETRIES):
            try:
                resp = requests.post(
                    url,
                    json={"chat_id": config.TELEGRAM_CHAT_ID, "text": message},
                    timeout=10
                )
                resp.raise_for_status()
                logger.info("Telegram sent")
                return True
            
            except Exception as e:
                logger.warning(f"Telegram attempt {attempt + 1} failed: {e}")
                if attempt < AlertService.MAX_RETRIES - 1:
                    import time
                    time.sleep(2 ** attempt)
        
        logger.error(f"Telegram failed after {AlertService.MAX_RETRIES} attempts")
        return False
    
    @staticmethod
    def notify_trade_opened(symbol: str, side: str, qty: int, entry_price: float, sl: float, tg: float):
        """Notify on trade open"""
        msg = f"🚀 Trade Opened\n{symbol} {side} {qty} @ ₹{entry_price:.2f}\nSL: ₹{sl:.2f} | TG: ₹{tg:.2f}"
        AlertService.send_telegram(msg)
        AlertService.send_email("Trade Opened", msg)
    
    @staticmethod
    def notify_trade_closed(symbol: str, pnl: float, pnl_pct: float, reason: str):
        """Notify on trade close"""
        emoji = "✅" if pnl > 0 else "❌"
        msg = f"{emoji} Trade Closed: {symbol}\nP&L: ₹{pnl:.2f} ({pnl_pct:.2f}%)\nReason: {reason}"
        AlertService.send_telegram(msg)
        AlertService.send_email("Trade Closed", msg)
    
    @staticmethod
    def notify_error(error_msg: str):
        """Notify on error"""
        AlertService.send_telegram(f"⚠️ Trading Engine Error: {error_msg}")
        AlertService.send_email("Trading Engine Error", error_msg)
