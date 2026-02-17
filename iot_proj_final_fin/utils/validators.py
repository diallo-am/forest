import re
from decimal import Decimal, InvalidOperation

class DataValidator:
    """Validation des données entrantes"""
    
    @staticmethod
    def validate_mac_address(mac):
        """Valide une adresse MAC"""
        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(pattern, mac))
    
    @staticmethod
    def validate_ip_address(ip):
        """Valide une adresse IP v4"""
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    
    @staticmethod
    def validate_sensor_value(value, min_val=None, max_val=None):
        """Valide une valeur de capteur"""
        try:
            val = Decimal(str(value))
            if min_val is not None and val < Decimal(str(min_val)):
                return False
            if max_val is not None and val > Decimal(str(max_val)):
                return False
            return True
        except (InvalidOperation, ValueError):
            return False
    
    @staticmethod
    def validate_api_key(api_key):
        """Valide le format d'une clé API"""
        if not api_key or len(api_key) < 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', api_key))
    
    @staticmethod
    def sanitize_string(text, max_length=None):
        """Nettoie une chaîne de caractères"""
        if not isinstance(text, str):
            return ""
        # Supprimer les caractères dangereux
        cleaned = re.sub(r'[<>"\']', '', text)
        if max_length:
            cleaned = cleaned[:max_length]
        return cleaned.strip()
