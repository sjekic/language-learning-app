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
        const apiUrl = 'https://linguee-api.fly.dev/api/v2/translations';
        console.log(`Forwarding to: ${apiUrl}?query=${query}&src=${src}&dst=${dst}`);

        const response = await axios.get(apiUrl, {
            params: {
                query,
                src,
                dst,
                guess_direction: false
            }
        });

        console.log('Linguee API Response Status:', response.status);
        console.log('Linguee API Response Data:', JSON.stringify(response.data).substring(0, 200) + '...'); // Log first 200 chars

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
