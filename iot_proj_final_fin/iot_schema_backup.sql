-- MySQL dump 10.13  Distrib 8.0.44, for Linux (x86_64)
--
-- Host: localhost    Database: iot_db
-- ------------------------------------------------------
-- Server version	8.0.44-0ubuntu0.24.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `alertes`
--

DROP TABLE IF EXISTS `alertes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alertes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `capteur_id` int NOT NULL,
  `noeud_id` int DEFAULT NULL,
  `type_alerte` enum('seuil_min','seuil_max','anomalie','hors_ligne','autre') NOT NULL,
  `severite` enum('info','warning','critical') NOT NULL,
  `seuil_min` decimal(10,4) DEFAULT NULL,
  `seuil_max` decimal(10,4) DEFAULT NULL,
  `message` text,
  `email_notification` tinyint(1) DEFAULT '1',
  `actif` tinyint(1) DEFAULT '1',
  `date_creation` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `noeud_id` (`noeud_id`),
  KEY `idx_actif` (`actif`),
  KEY `idx_capteur` (`capteur_id`),
  CONSTRAINT `alertes_ibfk_1` FOREIGN KEY (`capteur_id`) REFERENCES `capteurs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `alertes_ibfk_2` FOREIGN KEY (`noeud_id`) REFERENCES `noeuds` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alertes`
--

LOCK TABLES `alertes` WRITE;
/*!40000 ALTER TABLE `alertes` DISABLE KEYS */;
/*!40000 ALTER TABLE `alertes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `capteurs`
--

DROP TABLE IF EXISTS `capteurs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `capteurs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nom` varchar(100) NOT NULL,
  `type` varchar(50) NOT NULL,
  `unite` varchar(20) DEFAULT NULL,
  `description` text,
  `actif` tinyint(1) DEFAULT '1',
  `date_creation` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `date_modification` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_type` (`type`),
  KEY `idx_actif` (`actif`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `capteurs`
--

LOCK TABLES `capteurs` WRITE;
/*!40000 ALTER TABLE `capteurs` DISABLE KEYS */;
INSERT INTO `capteurs` VALUES (1,'Capteur Température 1','temperature','°C','Capteur de température ambiante',1,'2025-11-27 22:54:02','2025-11-27 22:54:02');
/*!40000 ALTER TABLE `capteurs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `logs`
--

DROP TABLE IF EXISTS `logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `noeud_id` int DEFAULT NULL,
  `niveau` enum('debug','info','warning','error','critical') NOT NULL,
  `action` varchar(100) DEFAULT NULL,
  `message` text,
  `adresse_ip` varchar(45) DEFAULT NULL,
  `user_agent` text,
  `details` json DEFAULT NULL,
  `timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_niveau` (`niveau`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_noeud` (`noeud_id`),
  CONSTRAINT `logs_ibfk_1` FOREIGN KEY (`noeud_id`) REFERENCES `noeuds` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `logs`
--

LOCK TABLES `logs` WRITE;
/*!40000 ALTER TABLE `logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `logs_alertes`
--

DROP TABLE IF EXISTS `logs_alertes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `logs_alertes` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `alerte_id` int NOT NULL,
  `mesure_id` bigint DEFAULT NULL,
  `valeur_mesuree` decimal(10,4) DEFAULT NULL,
  `message` text,
  `email_envoye` tinyint(1) DEFAULT '0',
  `date_email` timestamp NULL DEFAULT NULL,
  `timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `mesure_id` (`mesure_id`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_alerte` (`alerte_id`),
  CONSTRAINT `logs_alertes_ibfk_1` FOREIGN KEY (`alerte_id`) REFERENCES `alertes` (`id`) ON DELETE CASCADE,
  CONSTRAINT `logs_alertes_ibfk_2` FOREIGN KEY (`mesure_id`) REFERENCES `mesures` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `logs_alertes`
--

LOCK TABLES `logs_alertes` WRITE;
/*!40000 ALTER TABLE `logs_alertes` DISABLE KEYS */;
/*!40000 ALTER TABLE `logs_alertes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `mesures`
--

DROP TABLE IF EXISTS `mesures`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mesures` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `noeud_id` int NOT NULL,
  `capteur_id` int NOT NULL,
  `valeur` decimal(10,4) NOT NULL,
  `timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `metadata` json DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_noeud_timestamp` (`noeud_id`,`timestamp`),
  KEY `idx_capteur_timestamp` (`capteur_id`,`timestamp`),
  KEY `idx_timestamp` (`timestamp`),
  CONSTRAINT `mesures_ibfk_1` FOREIGN KEY (`noeud_id`) REFERENCES `noeuds` (`id`) ON DELETE CASCADE,
  CONSTRAINT `mesures_ibfk_2` FOREIGN KEY (`capteur_id`) REFERENCES `capteurs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `mesures`
--

LOCK TABLES `mesures` WRITE;
/*!40000 ALTER TABLE `mesures` DISABLE KEYS */;
/*!40000 ALTER TABLE `mesures` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `noeud_capteur`
--

DROP TABLE IF EXISTS `noeud_capteur`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `noeud_capteur` (
  `id` int NOT NULL AUTO_INCREMENT,
  `noeud_id` int NOT NULL,
  `capteur_id` int NOT NULL,
  `date_association` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_noeud_capteur` (`noeud_id`,`capteur_id`),
  KEY `capteur_id` (`capteur_id`),
  CONSTRAINT `noeud_capteur_ibfk_1` FOREIGN KEY (`noeud_id`) REFERENCES `noeuds` (`id`) ON DELETE CASCADE,
  CONSTRAINT `noeud_capteur_ibfk_2` FOREIGN KEY (`capteur_id`) REFERENCES `capteurs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `noeud_capteur`
--

LOCK TABLES `noeud_capteur` WRITE;
/*!40000 ALTER TABLE `noeud_capteur` DISABLE KEYS */;
INSERT INTO `noeud_capteur` VALUES (1,1,1,'2025-11-27 22:59:20');
/*!40000 ALTER TABLE `noeud_capteur` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `noeuds`
--

DROP TABLE IF EXISTS `noeuds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `noeuds` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nom` varchar(100) NOT NULL,
  `adresse_mac` varchar(17) NOT NULL,
  `adresse_ip` varchar(45) DEFAULT NULL,
  `localisation` varchar(200) DEFAULT NULL,
  `modele` varchar(100) DEFAULT NULL,
  `firmware_version` varchar(50) DEFAULT NULL,
  `statut` enum('actif','inactif','maintenance','erreur') DEFAULT 'actif',
  `derniere_connexion` timestamp NULL DEFAULT NULL,
  `api_key` varchar(64) NOT NULL,
  `date_creation` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `date_modification` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `adresse_mac` (`adresse_mac`),
  UNIQUE KEY `api_key` (`api_key`),
  KEY `idx_statut` (`statut`),
  KEY `idx_api_key` (`api_key`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `noeuds`
--

LOCK TABLES `noeuds` WRITE;
/*!40000 ALTER TABLE `noeuds` DISABLE KEYS */;
INSERT INTO `noeuds` VALUES (1,'Noeud Foret 1','00:1B:44:11:3A:B7','192.168.1.100','Tetouan','ESP32-DevKit',NULL,'actif',NULL,'noeud_api_key_001_abcdef123456','2025-11-27 22:55:26','2025-11-27 22:55:26');
/*!40000 ALTER TABLE `noeuds` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `utilisateurs`
--

DROP TABLE IF EXISTS `utilisateurs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `utilisateurs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('admin','user','readonly') DEFAULT 'user',
  `api_token` varchar(64) DEFAULT NULL,
  `token_expiration` timestamp NULL DEFAULT NULL,
  `actif` tinyint(1) DEFAULT '1',
  `derniere_connexion` timestamp NULL DEFAULT NULL,
  `date_creation` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `api_token` (`api_token`),
  KEY `idx_api_token` (`api_token`),
  KEY `idx_email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `utilisateurs`
--

LOCK TABLES `utilisateurs` WRITE;
/*!40000 ALTER TABLE `utilisateurs` DISABLE KEYS */;
INSERT INTO `utilisateurs` VALUES (1,'admin','admin@iot.local','$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5K3Kq5sK5sK5K','admin','admin_token_abcdef123456789',NULL,1,NULL,'2025-11-27 23:03:42');
/*!40000 ALTER TABLE `utilisateurs` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-28  0:05:01
