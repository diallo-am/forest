import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from threading import Thread
from config import Config
from database import db
from utils.logger import logger

class EmailNotification:
    """Système de notification par email"""
    
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.username = Config.SMTP_USERNAME
        self.password = Config.SMTP_PASSWORD
        self.from_email = Config.SMTP_FROM
        self.alert_cache = {}
    
    def send_email(self, to_email, subject, body, html=True):
        """Envoie un email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email envoyé à {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            return False
    
    def can_send_alert(self, alerte_id):
        """Vérifie si on peut envoyer une alerte avec délai minimum"""
        now = datetime.now()
        cache_key = f"alert_{alerte_id}"
        
        if cache_key in self.alert_cache:
            last_sent, count = self.alert_cache[cache_key]
            
            # Délai minimum : 2 minutes
            min_delay = timedelta(minutes=30)
            
            if now - last_sent < min_delay:
                seconds_remaining = (min_delay - (now - last_sent)).total_seconds()
                logger.info(f"Alerte {cache_key} en cooldown: {seconds_remaining:.0f}s restantes")
                return False
            else:
                self.alert_cache[cache_key] = (now, count + 1)
                logger.info(f"Envoi alerte {cache_key} autorisé")
                return True
        else:
            self.alert_cache[cache_key] = (now, 1)
            return True
    
    def send_alert_notification(self, alerte_id, log_alerte_id, valeur, message):
        """Envoie une notification d'alerte"""
        if not self.can_send_alert(alerte_id):
            return False
        
        try:
            query = """
                SELECT a.*, c.nom as capteur_nom, c.type, c.unite,
                       n.nom as noeud_nom, n.localisation
                FROM alertes a
                JOIN capteurs c ON a.capteur_id = c.id
                LEFT JOIN noeuds n ON a.noeud_id = n.id
                WHERE a.id = %s
            """
            alerte = db.execute_query(query, (alerte_id,))[0]
            
            emails_query = "SELECT email FROM utilisateurs WHERE role = 'admin' AND actif = TRUE"
            admins = db.execute_query(emails_query)
            
            if not admins:
                logger.warning("Aucun admin pour recevoir les alertes")
                return False
            
            subject = f"Alerte IoT - {alerte['severite'].upper()}: {alerte['capteur_nom']}"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: {'#d32f2f' if alerte['severite'] == 'critical' else '#f57c00'};">
                    Alerte {alerte['severite'].upper()}
                </h2>
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
                    <p><strong>Capteur:</strong> {alerte['capteur_nom']} ({alerte['type']})</p>
                    <p><strong>Noeud:</strong> {alerte.get('noeud_nom', 'N/A')}</p>
                    <p><strong>Localisation:</strong> {alerte.get('localisation', 'N/A')}</p>
                    <p><strong>Valeur:</strong> {valeur}</p>
                    <p><strong>Message:</strong> {message}</p>
                    <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </body>
            </html>
            """
            
            for admin in admins:
                thread = Thread(target=self.send_email, args=(admin['email'], subject, body))
                thread.start()
            
            update_query = "UPDATE logs_alertes SET email_envoye = TRUE, date_email = NOW() WHERE id = %s"
            db.execute_query(update_query, (log_alerte_id,))
            
            logger.info(f"Email d'alerte envoyé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi notification: {e}")
            return False

email_notifier = EmailNotification()
