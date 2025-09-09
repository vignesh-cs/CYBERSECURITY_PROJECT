const express = require('express');
const pool = require('../database');
const router = express.Router();

router.get('/policies', async (req, res) => {
    try {
        const { rows } = await pool.query(`
            SELECT id, standard, control, description, required_action, severity, created_at
            FROM policies 
            ORDER BY 
                CASE severity 
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 4
                END,
                created_at DESC
        `);
        res.json(rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.post('/policies', async (req, res) => {
    try {
        const { id, standard, control, description, required_action, severity } = req.body;
        
        const { rows } = await pool.query(`
            INSERT INTO policies (id, standard, control, description, required_action, severity)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        `, [id, standard, control, description, required_action, severity]);

        res.status(201).json(rows[0]);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.put('/policies/:id', async (req, res) => {
    try {
        const { id } = req.params;
        const { standard, control, description, required_action, severity } = req.body;
        
        const { rows } = await pool.query(`
            UPDATE policies 
            SET standard = $1, control = $2, description = $3, required_action = $4, severity = $5
            WHERE id = $6
            RETURNING *
        `, [standard, control, description, required_action, severity, id]);

        if (rows.length === 0) {
            return res.status(404).json({ error: 'Policy not found' });
        }

        res.json(rows[0]);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;