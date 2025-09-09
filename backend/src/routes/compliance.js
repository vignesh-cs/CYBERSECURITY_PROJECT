const express = require('express');
const pool = require('../database');
const router = express.Router();

router.get('/compliance/actions', async (req, res) => {
    try {
        const { severity, status, limit = 100, offset = 0 } = req.query;
        
        let query = `
            SELECT ca.*, p.standard, p.control, p.description as policy_description
            FROM compliance_actions ca
            LEFT JOIN policies p ON ca.policy_id = p.id
            WHERE 1=1
        `;
        const params = [];
        let paramCount = 0;

        if (severity) {
            paramCount++;
            query += ` AND p.severity = $${paramCount}`;
            params.push(severity.toUpperCase());
        }

        if (status) {
            paramCount++;
            query += ` AND ca.status = $${paramCount}`;
            params.push(status.toUpperCase());
        }

        query += ` ORDER BY ca.created_at DESC LIMIT $${paramCount + 1} OFFSET $${paramCount + 2}`;
        params.push(parseInt(limit), parseInt(offset));

        const { rows } = await pool.query(query, params);
        res.json(rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.get('/compliance/actions/:id', async (req, res) => {
    try {
        const { id } = req.params;
        
        const { rows } = await pool.query(`
            SELECT ca.*, p.standard, p.control, p.description as policy_description
            FROM compliance_actions ca
            LEFT JOIN policies p ON ca.policy_id = p.id
            WHERE ca.id = $1
        `, [id]);

        if (rows.length === 0) {
            return res.status(404).json({ error: 'Compliance action not found' });
        }

        res.json(rows[0]);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.post('/compliance/actions', async (req, res) => {
    try {
        const { policy_id, action_taken, threat_description, confidence, target_endpoints } = req.body;
        
        const { rows } = await pool.query(`
            INSERT INTO compliance_actions 
            (policy_id, action_taken, threat_description, confidence, target_endpoints, status)
            VALUES ($1, $2, $3, $4, $5, 'PENDING')
            RETURNING *
        `, [policy_id, action_taken, threat_description, confidence, target_endpoints]);

        res.status(201).json(rows[0]);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.get('/compliance/stats', async (req, res) => {
    try {
        const { days = 30 } = req.query;
        
        const stats = await pool.query(`
            SELECT 
                p.severity,
                ca.status,
                COUNT(*) as count,
                AVG(ca.confidence) as avg_confidence
            FROM compliance_actions ca
            LEFT JOIN policies p ON ca.policy_id = p.id
            WHERE ca.created_at >= NOW() - INTERVAL '${days} days'
            GROUP BY p.severity, ca.status
            ORDER BY p.severity, ca.status
        `);

        const summary = await pool.query(`
            SELECT 
                COUNT(*) as total_actions,
                COUNT(CASE WHEN status = 'EXECUTED' THEN 1 END) as successful_actions,
                COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_actions,
                AVG(confidence) as overall_confidence
            FROM compliance_actions
            WHERE created_at >= NOW() - INTERVAL '${days} days'
        `);

        res.json({
            by_severity: stats.rows,
            summary: summary.rows[0]
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;