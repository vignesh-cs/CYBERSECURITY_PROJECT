-- =============================================
-- Cybersecurity Compliance System Database
-- Complete Initialization Script
-- =============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================
-- 1. SYSTEM CONFIGURATION TABLES
-- =============================================

-- System Settings Table
CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    setting_key VARCHAR(255) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    setting_type VARCHAR(50) DEFAULT 'string',
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) DEFAULT 'system',
    updated_by VARCHAR(255) DEFAULT 'system'
);

-- Audit Log Table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    event_action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    user_id VARCHAR(255),
    user_ip VARCHAR(45),
    user_agent TEXT,
    details JSONB,
    status VARCHAR(50) DEFAULT 'SUCCESS',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- 2. USER MANAGEMENT TABLES
-- =============================================

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) DEFAULT 'USER' CHECK (role IN ('ADMIN', 'AUDITOR', 'OPERATOR', 'VIEWER')),
    department VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_locked BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret TEXT,
    password_changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) DEFAULT 'system',
    updated_by VARCHAR(255) DEFAULT 'system'
);

-- User Sessions Table
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token TEXT NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    device_info JSONB,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- API Keys Table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_name VARCHAR(255) NOT NULL,
    api_key TEXT NOT NULL,
    api_secret TEXT NOT NULL,
    permissions JSONB DEFAULT '[]'::jsonb,
    rate_limit_per_minute INTEGER DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    last_used TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- 3. COMPLIANCE FRAMEWORK TABLES
-- =============================================

-- Compliance Frameworks Table
CREATE TABLE compliance_frameworks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    framework_name VARCHAR(255) NOT NULL,
    framework_version VARCHAR(50),
    description TEXT,
    vendor VARCHAR(100),
    applicable_regions JSONB DEFAULT '[]'::jsonb,
    metadata JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

-- Compliance Policies Table
CREATE TABLE compliance_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    framework_id UUID REFERENCES compliance_frameworks(id),
    policy_code VARCHAR(100) UNIQUE NOT NULL,
    policy_name VARCHAR(255) NOT NULL,
    policy_description TEXT,
    policy_category VARCHAR(100),
    policy_rules JSONB NOT NULL,
    severity_level VARCHAR(50) CHECK (severity_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    priority INTEGER DEFAULT 1,
    implementation_guidance TEXT,
    remediation_steps TEXT,
    policy_references JSONB,  -- ← FIXED: Changed 'references' to 'policy_references'
    is_automated BOOLEAN DEFAULT FALSE,
    check_frequency VARCHAR(50) DEFAULT 'DAILY',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

-- =============================================
-- 4. ASSET MANAGEMENT TABLES
-- =============================================

-- Asset Types Table
CREATE TABLE asset_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    metadata_schema JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Assets Table
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_name VARCHAR(255) NOT NULL,
    asset_type_id UUID REFERENCES asset_types(id),
    asset_id VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    ip_address VARCHAR(45),
    hostname VARCHAR(255),
    operating_system VARCHAR(100),
    os_version VARCHAR(100),
    environment VARCHAR(50) CHECK (environment IN ('PRODUCTION', 'STAGING', 'DEVELOPMENT', 'TEST')),
    criticality VARCHAR(50) CHECK (criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    owner VARCHAR(255),
    department VARCHAR(100),
    location VARCHAR(255),
    metadata JSONB,
    tags JSONB DEFAULT '[]'::jsonb,
    is_monitored BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    last_seen TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

-- =============================================
-- 5. COMPLIANCE CHECK TABLES
-- =============================================

-- Compliance Checks Table
CREATE TABLE compliance_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id UUID REFERENCES compliance_policies(id),
    check_name VARCHAR(255) NOT NULL,
    check_code VARCHAR(100) UNIQUE NOT NULL,
    check_description TEXT,
    check_type VARCHAR(100) NOT NULL CHECK (check_type IN ('AUTOMATED', 'MANUAL', 'AI_POWERED')),
    target_asset_type UUID REFERENCES asset_types(id),
    check_parameters JSONB,
    technical_implementation TEXT,
    required_permissions JSONB,
    timeout_seconds INTEGER DEFAULT 300,
    schedule_cron VARCHAR(50),
    is_scheduled BOOLEAN DEFAULT FALSE,
    last_run TIMESTAMP WITH TIME ZONE,
    next_run TIMESTAMP WITH TIME ZONE,
    average_execution_time INTEGER,
    success_rate DECIMAL(5,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

-- Check Results Table
CREATE TABLE check_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    check_id UUID REFERENCES compliance_checks(id),
    asset_id UUID REFERENCES assets(id),
    status VARCHAR(50) CHECK (status IN ('PASS', 'FAIL', 'ERROR', 'PENDING', 'WARNING')),
    result_score DECIMAL(5,2),
    result_details JSONB,
    raw_output TEXT,
    evidence_data JSONB,
    severity VARCHAR(50) CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    confidence_score DECIMAL(5,4),
    execution_time_ms INTEGER,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    blockchain_tx_hash VARCHAR(255),
    blockchain_block_number BIGINT,
    blockchain_verified BOOLEAN DEFAULT FALSE,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- 6. AI ENGINE TABLES
-- =============================================

-- AI Models Table
CREATE TABLE ai_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL,
    model_version VARCHAR(100),
    model_type VARCHAR(100) CHECK (model_type IN ('CLASSIFICATION', 'REGRESSION', 'ANOMALY_DETECTION', 'NLP')),
    description TEXT,
    model_path TEXT,
    input_schema JSONB,
    output_schema JSONB,
    accuracy_score DECIMAL(5,4),
    precision_score DECIMAL(5,4),
    recall_score DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    training_data_size INTEGER,
    last_trained TIMESTAMP WITH TIME ZONE,
    is_production BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI Model Results Table
CREATE TABLE ai_model_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES ai_models(id),
    check_result_id UUID REFERENCES check_results(id),
    input_data JSONB,
    prediction_result JSONB,
    confidence_score DECIMAL(5,4),
    execution_time_ms INTEGER,
    model_version VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI Training Jobs Table
CREATE TABLE ai_training_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES ai_models(id),
    job_name VARCHAR(255),
    status VARCHAR(50) CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    training_data_path TEXT,
    parameters JSONB,
    metrics JSONB,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- 7. ENFORCEMENT ENGINE TABLES
-- =============================================

-- Enforcement Actions Table
CREATE TABLE enforcement_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    result_id UUID REFERENCES check_results(id),
    action_type VARCHAR(100) NOT NULL CHECK (action_type IN ('REMEDIATE', 'QUARANTINE', 'ALERT', 'BLOCK', 'NOTIFY')),
    action_name VARCHAR(255) NOT NULL,
    action_description TEXT,
    action_parameters JSONB,
    target_asset_id UUID REFERENCES assets(id),
    status VARCHAR(50) CHECK (status IN ('PENDING', 'EXECUTING', 'COMPLETED', 'FAILED', 'ROLLED_BACK')),
    scheduled_for TIMESTAMP WITH TIME ZONE,
    executed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_details JSONB,
    error_message TEXT,
    rollback_possible BOOLEAN DEFAULT FALSE,
    rollback_performed BOOLEAN DEFAULT FALSE,
    rollback_details JSONB,
    approval_required BOOLEAN DEFAULT FALSE,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Enforcement Templates Table
CREATE TABLE enforcement_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_name VARCHAR(255) NOT NULL,
    template_type VARCHAR(100),
    description TEXT,
    playbook_content TEXT,
    parameters_schema JSONB,
    supported_platforms JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

-- =============================================
-- 8. BLOCKCHAIN INTEGRATION TABLES
-- =============================================

-- Blockchain Transactions Table
CREATE TABLE blockchain_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_hash VARCHAR(255) UNIQUE NOT NULL,
    block_number BIGINT,
    block_hash VARCHAR(255),
    channel_name VARCHAR(255),
    chaincode_name VARCHAR(255),
    function_name VARCHAR(255),
    transaction_type VARCHAR(100),
    status VARCHAR(50) CHECK (status IN ('PENDING', 'COMMITTED', 'FAILED')),
    payload_hash VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Blockchain Assets Table
CREATE TABLE blockchain_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID REFERENCES assets(id),
    blockchain_asset_id VARCHAR(255),
    chaincode_name VARCHAR(255),
    channel_name VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- 9. NOTIFICATION & ALERTING TABLES
-- =============================================

-- Notification Templates Table
CREATE TABLE notification_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_name VARCHAR(255) NOT NULL,
    template_type VARCHAR(100) CHECK (template_type IN ('EMAIL', 'SLACK', 'SMS', 'WEBHOOK')),
    subject_template TEXT,
    body_template TEXT,
    variables JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Notifications Table
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES notification_templates(id),
    recipient_type VARCHAR(50) CHECK (recipient_type IN ('USER', 'GROUP', 'CHANNEL')),
    recipient_address TEXT,
    subject TEXT,
    body TEXT,
    priority VARCHAR(50) CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')),
    status VARCHAR(50) CHECK (status IN ('PENDING', 'SENT', 'FAILED', 'DELIVERED')),
    sent_at TIMESTAMP WITH TIME ZONE,
    delivery_confirmation JSONB,
    related_entity_type VARCHAR(100),
    related_entity_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- 10. INDEXES FOR PERFORMANCE
-- =============================================

-- Users Indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Sessions Indexes
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);

-- Compliance Indexes
CREATE INDEX idx_compliance_policies_framework ON compliance_policies(framework_id);
CREATE INDEX idx_compliance_policies_active ON compliance_policies(is_active);

-- Assets Indexes
CREATE INDEX idx_assets_asset_id ON assets(asset_id);
CREATE INDEX idx_assets_ip_address ON assets(ip_address);
CREATE INDEX idx_assets_hostname ON assets(hostname);
CREATE INDEX idx_assets_type ON assets(asset_type_id);

-- Check Results Indexes
CREATE INDEX idx_check_results_check_id ON check_results(check_id);
CREATE INDEX idx_check_results_asset_id ON check_results(asset_id);
CREATE INDEX idx_check_results_status ON check_results(status);
CREATE INDEX idx_check_results_created_at ON check_results(created_at);
CREATE INDEX idx_check_results_blockchain ON check_results(blockchain_tx_hash);

-- Enforcement Indexes
CREATE INDEX idx_enforcement_actions_result ON enforcement_actions(result_id);
CREATE INDEX idx_enforcement_actions_status ON enforcement_actions(status);

-- Blockchain Indexes
CREATE INDEX idx_blockchain_tx_hash ON blockchain_transactions(transaction_hash);
CREATE INDEX idx_blockchain_block_number ON blockchain_transactions(block_number);

-- Notification Indexes
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

-- =============================================
-- 11. DEFAULT DATA INSERTION
-- =============================================

-- Insert default system settings
INSERT INTO system_settings (setting_key, setting_value, setting_type, description, is_encrypted) VALUES
('system.name', 'Cybersecurity Compliance System', 'string', 'System display name', false),
('system.version', '1.0.0', 'string', 'System version', false),
('system.maintenance_mode', 'false', 'boolean', 'Maintenance mode status', false),
('system.auto_update', 'true', 'boolean', 'Automatic update checking', false),
('security.password_min_length', '12', 'number', 'Minimum password length', false),
('security.password_require_complexity', 'true', 'boolean', 'Password complexity requirement', false),
('security.session_timeout_minutes', '60', 'number', 'Session timeout duration', false),
('security.max_login_attempts', '5', 'number', 'Maximum login attempts before lockout', false),
('blockchain.enabled', 'true', 'boolean', 'Blockchain integration status', false),
('ai.enabled', 'true', 'boolean', 'AI engine status', false),
('logging.level', 'INFO', 'string', 'System logging level', false),
('notification.email_enabled', 'true', 'boolean', 'Email notification status', false),
('notification.slack_enabled', 'false', 'boolean', 'Slack notification status', false)
ON CONFLICT (setting_key) DO NOTHING;

-- Insert default asset types
INSERT INTO asset_types (type_name, description, metadata_schema) VALUES
('SERVER', 'Physical or virtual server', '{"cpu_cores": "number", "memory_gb": "number", "storage_gb": "number"}'),
('NETWORK_DEVICE', 'Router, switch, firewall', '{"model": "string", "firmware_version": "string", "ports": "number"}'),
('DATABASE', 'Database server', '{"db_engine": "string", "version": "string", "size_gb": "number"}'),
('APPLICATION', 'Software application', '{"version": "string", "programming_language": "string", "framework": "string"}'),
('CLOUD_INSTANCE', 'Cloud computing instance', '{"cloud_provider": "string", "instance_type": "string", "region": "string"}'),
('CONTAINER', 'Docker or container instance', '{"image_name": "string", "image_version": "string", "ports": "array"}')
ON CONFLICT (type_name) DO NOTHING;

-- Insert default compliance frameworks
INSERT INTO compliance_frameworks (framework_name, framework_version, description, vendor, applicable_regions) VALUES
('NIST Cybersecurity Framework', '1.1', 'National Institute of Standards and Technology Cybersecurity Framework', 'NIST', '["US", "GLOBAL"]'),
('ISO 27001', '2022', 'Information security management standard', 'ISO', '["GLOBAL"]'),
('PCI DSS', '4.0', 'Payment Card Industry Data Security Standard', 'PCI SSC', '["GLOBAL"]'),
('HIPAA', '2023', 'Health Insurance Portability and Accountability Act', 'HHS', '["US"]'),
('GDPR', '2018', 'General Data Protection Regulation', 'EU', '["EU", "EEA"]'),
('SOC 2', '2022', 'Service Organization Control 2', 'AICPA', '["GLOBAL"]')
ON CONFLICT (framework_name, framework_version) DO NOTHING;

-- Insert default AI models
INSERT INTO ai_models (model_name, model_version, model_type, description, accuracy_score, is_production) VALUES
('threat_detection_v1', '1.0.0', 'ANOMALY_DETECTION', 'Network threat detection model', 0.95, true),
('compliance_classifier_v1', '1.0.0', 'CLASSIFICATION', 'Compliance violation classifier', 0.92, true),
('risk_assessment_v1', '1.0.0', 'REGRESSION', 'Cybersecurity risk assessment model', 0.88, false)
ON CONFLICT (model_name, model_version) DO NOTHING;

-- Insert default admin user (password: Admin123!@# - should be changed immediately)
INSERT INTO users (username, email, password_hash, first_name, last_name, role, is_active) VALUES
('admin', 'admin@compliance.system', crypt('Admin123!@#', gen_salt('bf')), 'System', 'Administrator', 'ADMIN', true)
ON CONFLICT (username) DO NOTHING;

-- Insert default notification templates
INSERT INTO notification_templates (template_name, template_type, subject_template, body_template, variables) VALUES
('compliance_violation_email', 'EMAIL', 'Compliance Violation Alert: {{check_name}}', 'Compliance check {{check_name}} failed on asset {{asset_name}}. Severity: {{severity}}. Details: {{details}}', '["check_name", "asset_name", "severity", "details"]'),
('system_alert_slack', 'SLACK', 'System Alert: {{alert_type}}', 'Alert: {{alert_message}}\nSeverity: {{severity}}\nTime: {{timestamp}}', '["alert_type", "alert_message", "severity", "timestamp"]'),
('enforcement_completion_sms', 'SMS', 'Enforcement action completed', 'Action {{action_name}} completed with status: {{status}} on asset: {{asset_name}}', '["action_name", "status", "asset_name"]')
ON CONFLICT (template_name) DO NOTHING;

-- =============================================
-- 12. FUNCTIONS AND TRIGGERS
-- =============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_compliance_policies_updated_at BEFORE UPDATE ON compliance_policies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_assets_updated_at BEFORE UPDATE ON assets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_compliance_checks_updated_at BEFORE UPDATE ON compliance_checks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_enforcement_actions_updated_at BEFORE UPDATE ON enforcement_actions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function for audit logging
CREATE OR REPLACE FUNCTION log_audit_event()
RETURNS TRIGGER AS $$
DECLARE
    old_data JSONB;
    new_data JSONB;
    audit_details JSONB;
BEGIN
    old_data := to_jsonb(OLD);
    new_data := to_jsonb(NEW);
    
    audit_details := jsonb_build_object(
        'table_name', TG_TABLE_NAME,
        'operation', TG_OP,
        'old_data', old_data,
        'new_data', new_data,
        'changed_fields', (
            SELECT jsonb_object_agg(key, value)
            FROM jsonb_each(new_data)
            WHERE (old_data -> key) IS DISTINCT FROM (new_data -> key)
        )
    );
    
    INSERT INTO audit_logs (event_type, event_action, resource_type, resource_id, details)
    VALUES ('DATA_CHANGE', TG_OP, TG_TABLE_NAME, NEW.id::text, audit_details);
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to generate unique asset IDs
CREATE OR REPLACE FUNCTION generate_asset_id(asset_type VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    prefix VARCHAR;
    new_id VARCHAR;
    counter INTEGER;
BEGIN
    prefix := upper(substring(asset_type from 1 for 3));
    SELECT COUNT(*) + 1 INTO counter FROM assets WHERE asset_id LIKE prefix || '%';
    new_id := prefix || LPAD(counter::text, 6, '0');
    RETURN new_id;
END;
$$ language 'plpgsql';

-- =============================================
-- 13. VIEWS FOR REPORTING
-- =============================================

-- View for compliance dashboard
CREATE OR REPLACE VIEW compliance_dashboard AS
SELECT 
    f.framework_name,
    p.policy_name,
    p.severity_level,
    COUNT(cr.id) as total_checks,
    COUNT(cr.id) FILTER (WHERE cr.status = 'PASS') as passed_checks,
    COUNT(cr.id) FILTER (WHERE cr.status = 'FAIL') as failed_checks,
    COUNT(cr.id) FILTER (WHERE cr.status = 'ERROR') as error_checks,
    ROUND((COUNT(cr.id) FILTER (WHERE cr.status = 'PASS') * 100.0 / NULLIF(COUNT(cr.id), 0)), 2) as compliance_rate
FROM compliance_frameworks f
LEFT JOIN compliance_policies p ON f.id = p.framework_id
LEFT JOIN compliance_checks cc ON p.id = cc.policy_id
LEFT JOIN check_results cr ON cc.id = cr.check_id
GROUP BY f.framework_name, p.policy_name, p.severity_level;

-- View for asset compliance status
CREATE OR REPLACE VIEW asset_compliance_status AS
SELECT 
    a.asset_name,
    a.asset_id,
    at.type_name as asset_type,
    a.environment,
    a.criticality,
    COUNT(cr.id) as total_checks,
    COUNT(cr.id) FILTER (WHERE cr.status = 'PASS') as passed_checks,
    COUNT(cr.id) FILTER (WHERE cr.status = 'FAIL') as failed_checks,
    ROUND((COUNT(cr.id) FILTER (WHERE cr.status = 'PASS') * 100.0 / NULLIF(COUNT(cr.id), 0)), 2) as compliance_score
FROM assets a
LEFT JOIN asset_types at ON a.asset_type_id = at.id
LEFT JOIN check_results cr ON a.id = cr.asset_id
GROUP BY a.asset_name, a.asset_id, at.type_name, a.environment, a.criticality;

-- =============================================
-- 14. FINAL MESSAGE
-- =============================================

DO $$ 
BEGIN
    RAISE NOTICE 'Database initialization completed successfully!';
    RAISE NOTICE 'Total tables created: 24';
    RAISE NOTICE 'Total indexes created: 20';
    RAISE NOTICE 'Default data inserted for system setup';
    RAISE NOTICE 'Admin user created: username=admin, password=Admin123!@# (change immediately)';
END $$;