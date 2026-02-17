import joblib
import numpy as np
import pandas as pd
from utils.logger import logger
import os

class FirePredictionModel:
    """Modèle IA pour prédire les risques d'incendie"""
    
    def __init__(self, model_path='models/fire_model.pkl'):
        """Initialiser et charger le modèle"""
        self.model = None
        self.model_path = model_path
        self.load_model()
    
    def load_model(self):
        """Charger le modèle Random Forest"""
        try:
            if not os.path.exists(self.model_path):
                logger.warning(f"Modèle IA non trouvé : {self.model_path}")
                logger.warning("Prédictions désactivées. Le système utilisera les seuils simples.")
                return False
            
            self.model = joblib.load(self.model_path)
            logger.info(f"✓ Modèle IA chargé depuis {self.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur chargement modèle IA : {e}")
            self.model = None
            return False
    
    def map_value(self, x, in_min, in_max, out_min, out_max):
        """Calibration des valeurs"""
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    
    def predict_fire_risk(self, temperature, humidity, raw_gas=None, smoke_level=None):
        """
        Prédire le risque d'incendie avec les 3 capteurs
        
        Args:
            temperature (float): Température en °C
            humidity (float): Humidité en %
            raw_gas (int): Valeur brute du capteur de gaz (optionnel)
            smoke_level (float): Niveau de fumée calibré (optionnel)
        
        Returns:
            dict: Résultat de la prédiction
        """
        
        # Si pas de modèle, utiliser des seuils simples
        if self.model is None:
            return self._simple_threshold_prediction(temperature, humidity, smoke_level)
        
        try:
            # Calibrer le gaz si nécessaire
            if raw_gas is not None and smoke_level is None:
                smoke_level = self.map_value(raw_gas, 0, 4095, 0, 1000)
            elif smoke_level is None:
                smoke_level = 0
            
            # Convertir en types Python natifs
            temperature = float(temperature)
            humidity = float(humidity)
            smoke_level = float(smoke_level)
            
            logger.info(f"Données IA: T={temperature}°C, H={humidity}%, Fumée={smoke_level:.1f}ppm")
            
            # Créer un DataFrame avec les noms de colonnes
            features_df = pd.DataFrame(
                [[temperature, humidity, smoke_level]], 
                columns=['temperature', 'humidity', 'raw_h2']
            )
            
            # Prédiction
            prediction = int(self.model.predict(features_df)[0])
            probabilities = self.model.predict_proba(features_df)[0]
            fire_risk_percent = float(probabilities[1] * 100)
            
            # Déterminer le statut
            if prediction == 1:
                status = 'CRITICAL'
            elif fire_risk_percent > 50:
                status = 'WARNING'
            else:
                status = 'SAFE'
            
            result = {
                'prediction': prediction,
                'fire_risk_percent': round(fire_risk_percent, 2),
                'status': status,
                'confidence': round(float(max(probabilities) * 100), 2),
                'smoke_level': round(smoke_level, 2)
            }
            
            logger.info(f"Prédiction IA: {status} - Risque: {fire_risk_percent:.1f}% (Confiance: {result['confidence']}%)")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur prédiction IA : {e}", exc_info=True)
            return self._simple_threshold_prediction(temperature, humidity, smoke_level)
    
    def _simple_threshold_prediction(self, temperature, humidity, smoke_level=None):
        """Méthode de fallback avec seuils simples"""
        fire_risk = 0
        
        # Convertir en float si nécessaire
        temperature = float(temperature) if temperature else 25.0
        humidity = float(humidity) if humidity else 50.0
        smoke_level = float(smoke_level) if smoke_level else 0.0
        
        # Logique simple basée sur les seuils
        if temperature > 35:
            fire_risk += 20
        if temperature > 40:
            fire_risk += 20
        if temperature > 50:
            fire_risk += 30
        
        if humidity < 30:
            fire_risk += 10
        if humidity < 20:
            fire_risk += 10
        
        if smoke_level > 200:
            fire_risk += 20
        if smoke_level > 400:
            fire_risk += 30
        
        fire_risk = min(fire_risk, 100)
        
        if fire_risk >= 70:
            status = 'CRITICAL'
            prediction = 1
        elif fire_risk >= 40:
            status = 'WARNING'
            prediction = 0
        else:
            status = 'SAFE'
            prediction = 0
        
        logger.info(f"Prédiction seuils simples: {status} - Risque: {fire_risk}%")
        
        return {
            'prediction': prediction,
            'fire_risk_percent': fire_risk,
            'status': status,
            'confidence': 75.0,
            'smoke_level': smoke_level
        }

# Instance globale
fire_model = FirePredictionModel()
