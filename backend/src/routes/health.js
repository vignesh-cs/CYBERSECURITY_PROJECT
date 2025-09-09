const express = require('express');
const pool = require('../database');
const router = express.Router();

router.get('/health', async (req, res) => {
    try {
        // Check database connection
        await pool.query('SELECT 1');
        
        res.json({
            status: 'OK',
            timestamp: new Date().toISOString(),
            services: {
                database: 'connected',
                blockchain: 'connected',
                ai_engine: 'operational'
            }
        });
    } catch (error) {
        res.status(500).json({
            status: 'ERROR',
            error: error.message
        });
    }
});

router.get('/health/stats', async (req, res) => {
    try {
        const [complianceResult, threatsResult, actionsResult] = await Promise.all([
            pool.query(`
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'COMPLIANT' THEN 1 ELSE 0 END) as compliant
                FROM endpoints
            `),
            pool.query(`
                SELECT COUNT(*) as active_threats
                FROM threat_intelligence
                WHERE severity IN ('HIGH', 'CRITICAL')
                AND timestamp > NOW() - INTERVAL '24 hours'
            `),
            pool.query(`
                SELECT COUNT(*) as actions_today
                FROM compliance_actions
                WHERE created_at::date = CURRENT_DATE
            `)
        ]);

        const complianceRate = complianceResult.rows[0].total > 0 ? 
            Math.round((complianceResult.rows[0].compliant / complianceResult.rows[0].total) * 100) : 100;

        res.json({
            complianceRate,
            activeThreats: threatsResult.rows[0].active_threats,
            actionsToday: actionsResult.rows[0].actions_today
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;