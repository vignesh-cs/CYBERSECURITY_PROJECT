const express = require('express');
const pool = require('../database');
const router = express.Router();

router.get('/threats', async (req, res) => {
    try {
        const { severity, source, limit = 50 } = req.query;
        
        let query = `
            SELECT * FROM threat_intelligence 
            WHERE 1=1
        `;
        const params = [];
        let paramCount = 0;

        if (severity) {
            paramCount++;
            query += ` AND severity = $${paramCount}`;
            params.push(severity.toUpperCase());
        }

        if (source) {
            paramCount++;
            query += ` AND source = $${paramCount}`;
            params.push(source);
        }

        query += ` ORDER BY created_at DESC LIMIT $${paramCount + 1}`;
        params.push(parseInt(limit));

        const { rows } = await pool.query(query, params);
        res.json(rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.get('/threats/stats', async (req, res) => {
    try {
        const { days = 7 } = req.query;
        
        const { rows } = await pool.query(`
            SELECT 
                severity,
                source,
                COUNT(*) as count,
                MAX(created_at) as latest
            FROM threat_intelligence
            WHERE created_at >= NOW() - INTERVAL '${days} days'
            GROUP BY severity, source
            ORDER BY severity, source
        `);

        res.json(rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.post('/threats', async (req, res) => {
    try {
        const { source, cve_id, ioc, title, description, severity, type, published_date, references } = req.body;
        
        const { rows } = await pool.query(`
            INSERT INTO threat_intelligence 
            (source, cve_id, ioc, title, description, severity, type, published_date, references)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        `, [source, cve_id, ioc, title, description, severity, type, published_date, references]);

        res.status(201).json(rows[0]);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;