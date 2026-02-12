import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import traceback

# Email Configuration
SMTP_SERVER = "smtppro.zoho.eu"
SMTP_PORT = 465
SMTP_USER = "info@aralbruehl.de"
SMTP_PASSWORD = "35gryuXW3h&e7*@%"
RECIPIENT_EMAIL = "vt@aralbruehl.de"

def send_email(subject, body):
    """
    Send an email using Zoho SMTP (SSL).
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        # Create secure connection with server and send email
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            
        print(f"[{datetime.now()}] Email sent: {subject}")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] Failed to send email: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Test execution
    send_email("Test Email from TradingAlert Server", "This is a test email to verify configuration.")
