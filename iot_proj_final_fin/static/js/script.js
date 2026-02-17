// ==================== CONFIGURATION ====================
const API_URL = window.location.origin + '/api';

// ==================== AUTHENTIFICATION ====================

function checkAuth() {
    const token = localStorage.getItem('iot_token');
    const currentPage = window.location.pathname;
    
    console.log('Vérification auth - Page:', currentPage, 'Token:', token ? 'présent' : 'absent');
    
    // Si pas de token et pas sur la page de login
    if (!token && currentPage !== '/' && !currentPage.includes('index')) {
        console.log('Pas de token, redirection vers login');
        window.location.href = '/';
        return false;
    }
    
    return true;
}

function logout() {
    if (confirm('Êtes-vous sûr de vouloir vous déconnecter ?')) {
        localStorage.removeItem('iot_token');
        localStorage.removeItem('iot_user');
        window.location.href = '/';
    }
}

// ==================== REQUÊTES API ====================

async function apiRequest(endpoint, options = {}) {
    const token = localStorage.getItem('iot_token');
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        }
    };
    
    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(`${API_URL}${endpoint}`, mergedOptions);
        
        // Si non autorisé, rediriger vers login
        if (response.status === 401) {
            console.log('401 Unauthorized - Redirection vers login');
            localStorage.removeItem('iot_token');
            localStorage.removeItem('iot_user');
            window.location.href = '/';
            return null;
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Erreur API');
        }
        
        return data;
        
    } catch (error) {
        console.error('Erreur API:', error);
        throw error;
    }
}


// ==================== FORMATAGE ====================

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDateShort(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function timeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    const intervals = {
        année: 31536000,
        mois: 2592000,
        semaine: 604800,
        jour: 86400,
        heure: 3600,
        minute: 60
    };
    
    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
        const interval = Math.floor(seconds / secondsInUnit);
        if (interval >= 1) {
            return `Il y a ${interval} ${unit}${interval > 1 ? 's' : ''}`;
        }
    }
    
    return 'À l\'instant';
}

// ==================== NOTIFICATIONS ====================

function showNotification(message, type = 'info') {
    // Créer l'élément de notification
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
        color: white;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 9999;
        animation: slideIn 0.3s;
    `;
    
    document.body.appendChild(notification);
    
    // Supprimer après 3 secondes
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Ajouter les animations CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ==================== VALIDATION ====================

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validateMacAddress(mac) {
    const re = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
    return re.test(mac);
}

function validateIP(ip) {
    const re = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!re.test(ip)) return false;
    
    const parts = ip.split('.');
    return parts.every(part => {
        const num = parseInt(part);
        return num >= 0 && num <= 255;
    });
}

// ==================== EXPORT DONNÉES ====================

function exportToCSV(data, filename = 'export.csv') {
    if (!data || data.length === 0) {
        alert('Aucune donnée à exporter');
        return;
    }
    
    // Obtenir les en-têtes
    const headers = Object.keys(data[0]);
    
    // Créer le CSV
    let csv = headers.join(',') + '\n';
    
    data.forEach(row => {
        const values = headers.map(header => {
            const value = row[header];
            return typeof value === 'string' && value.includes(',') 
                ? `"${value}"` 
                : value;
        });
        csv += values.join(',') + '\n';
    });
    
    // Télécharger
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
}

// ==================== INITIALISATION ====================

document.addEventListener('DOMContentLoaded', () => {
    // Vérifier l'authentification
    checkAuth();
    
    // Afficher les informations utilisateur
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.username) {
        console.log(`Connecté en tant que: ${user.username} (${user.role})`);
    }
});

// ==================== GESTION DES ERREURS GLOBALES ====================

window.addEventListener('unhandledrejection', (event) => {
    console.error('Erreur non gérée:', event.reason);
    showNotification('Une erreur est survenue', 'error');
});
