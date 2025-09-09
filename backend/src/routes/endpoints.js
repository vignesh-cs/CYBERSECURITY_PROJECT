const express = require('express');
const pool = require('../database');
const router = express.Router();

router.get('/endpoints', async (req, res) => {
    try {
        const { status, os_type } = req.query;
        
        let query = `SELECT * FROM endpoints WHERE 1=1`;
        const params = [];
        let paramCount = 0;

        if (status) {
            paramCount++;
            query += ` AND status = $${paramCount}`;
            params.push(status.toUpperCase());
        }

        if (os_type) {
            paramCount++;
            query += ` AND os_type ILIKE $${paramCount}`;
            params.push(`%${os_type}%`);
        }

        query += ` ORDER BY hostname`;

        const { rows } = await pool.query(query, params);
        res.json(rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.post('/endpoints', async (req, res) => {
    try {
        const { hostname, ip_address, os_type, os_version, status } = req.body;
        
        const { rows } = await pool.query(`
            INSERT INTO endpoints (hostname, ip_address, os_type, os_version, status)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (hostname) 
            DO UPDATE SET 
                ip_address = EXCLUDED.ip_address,
                os_type = EXCLUDED.os_type,
                os_version = EXCLUDED.os_version,
                status = EXCLUDED.status,
                last_seen = CURRENT_TIMESTAMP
            RETURNING *
        `, [hostname, ip_address, os_type, os_version, status]);

        res.status(201).json(rows[0]);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.put('/endpoints/:id/status', async (req, res) => {
    try {
        const { id } = req.params;
        const { status } = req.body;
        
        const { rows } = await pool.query(`
            UPDATE endpoints 
            SET status = $1, last_seen = CURRENT_TIMESTAMP
            WHERE id = $2
            RETURNING *
        `, [status, id]);

        if (rows.length === 0) {
            return res.status(404).json({ error: 'Endpoint not found' });
        }

        res.json(rows[0]);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;