class ComplianceManager {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 20;
        this.filters = {
            severity: '',
            status: '',
            search: ''
        };
    }

    async loadComplianceActions() {
        try {
            const params = new URLSearchParams({
                limit: this.pageSize,
                offset: (this.currentPage - 1) * this.pageSize,
                ...this.filters
            });

            const response = await fetch(`/api/compliance/actions?${params}`);
            if (!response.ok) throw new Error('Failed to fetch compliance actions');
            
            const actions = await response.json();
            this.displayComplianceActions(actions);
            this.updatePagination();
        } catch (error) {
            console.error('Error loading compliance actions:', error);
            this.showError('Failed to load compliance actions');
        }
    }

    displayComplianceActions(actions) {
        const tbody = document.getElementById('actions-body');
        tbody.innerHTML = '';

        actions.forEach(action => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${new Date(action.created_at).toLocaleString()}</td>
                <td>${action.action_taken}</td>
                <td>${action.policy_id}</td>
                <td class="severity-${action.severity?.toLowerCase() || 'unknown'}">
                    ${action.severity || 'N/A'}
                </td>
                <td class="status-${action.status.toLowerCase()}">${action.status}</td>
                <td>${action.confidence ? (action.confidence * 100).toFixed(1) + '%' : 'N/A'}</td>
                <td>
                    <button class="btn-info" onclick="app.showActionDetails('${action.id}')">
                        Details
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    updatePagination() {
        const pagination = document.getElementById('pagination');
        pagination.innerHTML = `
            <button ${this.currentPage === 1 ? 'disabled' : ''} 
                    onclick="complianceManager.previousPage()">Previous</button>
            <span>Page ${this.currentPage}</span>
            <button onclick="complianceManager.nextPage()">Next</button>
        `;
    }

    nextPage() {
        this.currentPage++;
        this.loadComplianceActions();
    }

    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadComplianceActions();
        }
    }

    applyFilters() {
        this.filters = {
            severity: document.getElementById('severity-filter').value,
            status: document.getElementById('status-filter').value,
            search: document.getElementById('search-actions').value.toLowerCase()
        };
        this.currentPage = 1;
        this.loadComplianceActions();
    }

    async showActionDetails(actionId) {
        try {
            const response = await fetch(`/api/compliance/actions/${actionId}`);
            if (!response.ok) throw new Error('Failed to fetch action details');
            
            const action = await response.json();
            this.displayActionDetails(action);
        } catch (error) {
            console.error('Error loading action details:', error);
            this.showError('Failed to load action details');
        }
    }

    displayActionDetails(action) {
        const modal = document.getElementById('action-details-modal');
        const content = document.getElementById('action-details-content');
        
        content.innerHTML = `
            <h3>Action Details</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <label>ID:</label>
                    <span>${action.id}</span>
                </div>
                <div class="detail-item">
                    <label>Action:</label>
                    <span>${action.action_taken}</span>
                </div>
                <div class="detail-item">
                    <label>Policy:</label>
                    <span>${action.policy_id} (${action.standard} ${action.control})</span>
                </div>
                <div class="detail-item">
                    <label>Status:</label>
                    <span class="status-${action.status.toLowerCase()}">${action.status}</span>
                </div>
                <div class="detail-item">
                    <label>Confidence:</label>
                    <span>${action.confidence ? (action.confidence * 100).toFixed(1) + '%' : 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <label>Created:</label>
                    <span>${new Date(action.created_at).toLocaleString()}</span>
                </div>
                <div class="detail-item full-width">
                    <label>Threat Description:</label>
                    <p>${action.threat_description || 'No description available'}</p>
                </div>
                <div class="detail-item full-width">
                    <label>Policy Description:</label>
                    <p>${action.policy_description || 'No description available'}</p>
                </div>
            </div>
        `;
        
        modal.style.display = 'block';
    }

    closeModal() {
        document.getElementById('action-details-modal').style.display = 'none';
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-notification';
        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #e74c3c;
            color: white;
            padding: 1rem;
            border-radius: 4px;
            z-index: 1000;
        `;
        
        document.body.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    }
}

// Initialize compliance manager
window.complianceManager = new ComplianceManager();

// Add modal close functionality
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('action-details-modal');
    const closeBtn = document.querySelector('.modal-close');
    
    closeBtn.onclick = function() {
        modal.style.display = 'none';
    };
    
    window.onclick = function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    };
});