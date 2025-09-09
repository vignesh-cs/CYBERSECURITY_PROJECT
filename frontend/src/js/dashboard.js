class Dashboard {
    constructor() {
        this.threatChart = null;
        this.complianceChart = null;
        this.initCharts();
    }

    initCharts() {
        this.createThreatChart();
        this.createComplianceChart();
    }

    createThreatChart() {
        const ctx = document.getElementById('threatChart').getContext('2d');
        this.threatChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    label: 'Threats by Severity',
                    data: [5, 12, 8, 3],
                    backgroundColor: [
                        '#e74c3c',
                        '#f39c12',
                        '#f1c40f',
                        '#2ecc71'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Threat Distribution'
                    }
                }
            }
        });
    }

    createComplianceChart() {
        const ctx = document.getElementById('complianceChart').getContext('2d');
        this.complianceChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Compliant', 'Non-Compliant'],
                datasets: [{
                    data: [85, 15],
                    backgroundColor: [
                        '#2ecc71',
                        '#e74c3c'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Compliance Status'
                    }
                }
            }
        });
    }

    updateCharts(threatData, complianceData) {
        if (this.threatChart) {
            this.threatChart.data.datasets[0].data = threatData;
            this.threatChart.update();
        }

        if (this.complianceChart) {
            this.complianceChart.data.datasets[0].data = complianceData;
            this.complianceChart.update();
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});