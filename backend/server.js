const express = require('express');
const cors = require('cors');
const axios = require('axios');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3001;

// Simple in-memory cache
const translationCache = new Map();

app.use(cors());
app.use(express.json());

// Linguee API Proxy Endpoint
app.get('/api/translate', async (req, res) => {
    try {
        const { query, src, dst } = req.query;

        if (!query || !src || !dst) {
            return res.status(400).json({ error: 'Missing required parameters: query, src, dst' });
        }

        // Check cache
        const cacheKey = `${src}:${dst}:${query.toLowerCase()}`;
        if (translationCache.has(cacheKey)) {
            console.log('Serving from cache:', cacheKey);
            return res.json(translationCache.get(cacheKey));
        }

        // Call Linguee API
        // Using the public Linguee API proxy mentioned in the user request
        const response = await axios.get('https://linguee-api.fly.dev/api/v2/translations', {
            params: {
                query,
                src,
                dst,
                guess_direction: false
            }
        });

        // Store in cache
        translationCache.set(cacheKey, response.data);

        res.json(response.data);
    } catch (error) {
        console.error('Translation error:', error.message);
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ error: 'Failed to fetch translation' });
        }
    }
});

app.listen(PORT, () => {
    console.log(`Backend server running on http://localhost:${PORT}`);
});
