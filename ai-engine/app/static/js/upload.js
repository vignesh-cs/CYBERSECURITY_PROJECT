class FileUploader {
    constructor() {
        this.uploadForm = document.getElementById('upload-form');
        this.fileInput = document.getElementById('file-input');
        this.threatInput = document.getElementById('threat-input');
        this.terminalOutput = document.getElementById('terminal-output');
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.uploadForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.addToTerminal(`📁 Selected file: ${file.name}`);
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData();
        const file = this.fileInput.files[0];
        const threatText = this.threatInput.value.trim();

        if (file) {
            formData.append('file', file);
            formData.append('file_type', this.getFileType(file.name));
            this.analyzeFile(formData);
        } else if (threatText) {
            this.analyzeText(threatText);
        } else {
            this.addToTerminal('❌ Please select a file or enter threat text');
        }
    }

    getFileType(filename) {
        if (filename.endsWith('.json')) return 'json';
        if (filename.endsWith('.log')) return 'log';
        if (filename.endsWith('.txt')) return 'text';
        return 'auto';
    }

    async analyzeFile(formData) {
        try {
            this.addToTerminal('📤 Uploading file for analysis...');
            
            const response = await fetch('/api/analyze-file', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Upload failed');
            
            const result = await response.json();
            this.addToTerminal(`✅ File processed: ${result.processed_threats} threats found`);
            this.addToTerminal(`🛠️ Actions taken: ${result.actions_taken}`);
            
        } catch (error) {
            this.addToTerminal(`❌ Error: ${error.message}`);
        }
    }

    async analyzeText(threatText) {
        try {
            this.addToTerminal('🔍 Analyzing threat text...');
            
            const response = await fetch('/api/analyze-threat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ description: threatText })
            });

            if (!response.ok) throw new Error('Analysis failed');
            
            const result = await response.json();
            this.addToTerminal(`✅ Analysis complete: ${result.results[0][0]}`);
            
        } catch (error) {
            this.addToTerminal(`❌ Error: ${error.message}`);
        }
    }

    addToTerminal(message) {
        const timestamp = new Date().toLocaleTimeString();
        const terminalLine = document.createElement('div');
        terminalLine.className = 'terminal-line';
        terminalLine.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
        
        this.terminalOutput.appendChild(terminalLine);
        this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight;
    }

    clearTerminal() {
        this.terminalOutput.innerHTML = '';
        this.addToTerminal('🚀 Terminal initialized. Ready for threats...');
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.fileUploader = new FileUploader();
});