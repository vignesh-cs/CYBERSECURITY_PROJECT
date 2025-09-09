class ComplianceApp {
    constructor() {
        this.apiBase = '/api';
        this.currentSection = 'dashboard';
        this.init();
    }

    init() {
        this.setupNavigation();
        this.loadInitialData();
        this.setupEventListeners();
    }

    setupNavigation() {
        const navLinks = document.querySelectorAll('nav a');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const sectionId = link.getAttribute('href').substring(1);
                this.showSection(sectionId);
            });
        });
    }

    showSection(sectionId) {
        // Hide all sections
        document.querySelectorAll('main section').forEach(section => {
            section.classList.remove('active');
        });

        // Show selected section
        document.getElementById(sectionId).classList.add('active');
        this.currentSection = sectionId;

        // Load section-specific data
        this.loadSectionData(sectionId);
    }

    async loadInitialData() {
        try {
            const [actions, policies, stats] = await Promise.all([
                this.fetchData('/compliance/actions'),
                this.fetchData('/policies'),
                this.fetchData('/health/stats')
            ]);

            this.updateDashboard(stats);
            this.updateComplianceActions(actions);
            this.updatePolicies(policies);
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showError('Failed to load data. Please try again.');
        }
    }

    async loadSectionData(sectionId) {
        try {
            switch (sectionId) {
                case 'compliance':
                    const actions = await this.fetchData('/compliance/actions');
                    this.updateComplianceActions(actions);
                    break;
                case 'policies':
                    const policies = await this.fetchData('/policies');
                    this.updatePolicies(policies);
                    break;
                case 'threats':
                    const threats = await this.fetchData('/threats');
                    this.updateThreats(threats);
                    break;
            }
        } catch (error) {
            console.error(`Failed to load ${sectionId} data:`, error);
        }
    }

    async fetchData(endpoint) {
        const response = await fetch(`${this.apiBase}${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    }

    updateDashboard(stats) {
        if (stats.complianceRate) {
            document.getElementById('compliance-rate').textContent = `${stats.complianceRate}%`;
        }
        if (stats.activeThreats) {
            document.getElementById('active-threats').textContent = stats.activeThreats;
        }
        if (stats.actionsToday) {
            document.getElementById('actions-today').textContent = stats.actionsToday;
        }
    }

    updateComplianceActions(actions) {
        const tbody = document.getElementById('actions-body');
        tbody.innerHTML = '';

        actions.forEach(action => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${new Date(action.timestamp).toLocaleString()}</td>
                <td>${action.actionTaken}</td>
                <td>${action.policyId}</td>
                <td class="severity-${action.severity?.toLowerCase()}">${action.severity}</td>
                <td>${action.status}</td>
            `;
            tbody.appendChild(row);
        });
    }

    updatePolicies(policies) {
        const container = document.getElementById('policies-list');
        container.innerHTML = '';

        policies.forEach(policy => {
            const card = document.createElement('div');
            card.className = 'policy-card';
            card.innerHTML = `
                <h3>${policy.standard} ${policy.control}</h3>
                <p>${policy.description}</p>
                <div class="policy-meta">
                    <span class="severity severity-${policy.severity.toLowerCase()}">${policy.severity}</span>
                    <span class="action">Action: ${policy.required_action}</span>
                </div>
            `;
            container.appendChild(card);
        });
    }

    updateThreats(threats) {
        const container = document.getElementById('threat-feed');
        container.innerHTML = '';

        threats.forEach(threat => {
            const card = document.createElement('div');
            card.className = `threat-card ${threat.severity.toLowerCase()}`;
            card.innerHTML = `
                <h3>${threat.title}</h3>
                <p>${threat.description}</p>
                <div class="threat-meta">
                    <span class="severity">${threat.severity}</span>
                    <span class="timestamp">${new Date(threat.timestamp).toLocaleString()}</span>
                </div>
            `;
            container.appendChild(card);
        });
    }

    setupEventListeners() {
        // Search and filter functionality
        const searchInput = document.getElementById('search-actions');
        const severityFilter = document.getElementById('severity-filter');

        if (searchInput && severityFilter) {
            searchInput.addEventListener('input', this.filterActions.bind(this));
            severityFilter.addEventListener('change', this.filterActions.bind(this));
        }

        // Auto-refresh data every 30 seconds
        setInterval(() => this.loadSectionData(this.currentSection), 30000);
    }

    filterActions() {
        const searchTerm = document.getElementById('search-actions').value.toLowerCase();
        const severityFilter = document.getElementById('severity-filter').value;

        const rows = document.querySelectorAll('#actions-body tr');
        rows.forEach(row => {
            const actionText = row.textContent.toLowerCase();
            const severity = row.querySelector('td:nth-child(4)').textContent;

            const matchesSearch = actionText.includes(searchTerm);
            const matchesSeverity = !severityFilter || severity === severityFilter;

            row.style.display = matchesSearch && matchesSeverity ? '' : 'none';
        });
    }

    showError(message) {
        // Create error notification
        const errorDiv = document.createElement('div');
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
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);

        setTimeout(() => {
            document.body.removeChild(errorDiv);
        }, 5000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ComplianceApp();
});