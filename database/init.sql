-- ==========================================
-- USERS (Firebase Authentication)
-- ==========================================
CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    firebase_uid    TEXT UNIQUE NOT NULL,  -- Firebase User ID
    email           TEXT UNIQUE NOT NULL,
    display_name    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for faster lookups by Firebase UID
CREATE INDEX IF NOT EXISTS idx_users_firebase_uid ON users (firebase_uid);

-- ==========================================
-- BOOKS (generated books)
-- ==========================================
CREATE TABLE IF NOT EXISTS books (
    id                  BIGSERIAL PRIMARY KEY,
    title               TEXT NOT NULL,
    description         TEXT,
    
    -- where the actual book text (PDF/EPUB/JSON/TXT) lives in blob storage
    text_blob_url       TEXT NOT NULL,
    
    -- where the cover image is stored
    cover_image_url     TEXT,
    
    language_code       VARCHAR(10) NOT NULL,   -- e.g. 'en', 'es', 'fr'
    level               VARCHAR(10),            -- e.g. 'A1','A2','B1','B2','C1','C2'
    genre               TEXT,                   -- 'mystery','fantasy', etc.
    
    is_pro_book         BOOLEAN NOT NULL DEFAULT FALSE,
    pages_estimate      INT,                    -- 20–30 for free, up to 100 for pro
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ==========================================
-- LINK TABLE: which user has which generated books
-- ==========================================
CREATE TABLE IF NOT EXISTS user_books (
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id             BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    
    -- extra useful fields
    is_owner            BOOLEAN NOT NULL DEFAULT TRUE,  -- user who generated it
    is_favorite         BOOLEAN NOT NULL DEFAULT FALSE,
    last_opened_at      TIMESTAMPTZ,
    progress_percent    NUMERIC(5,2),                   -- e.g. 37.50 (% read)
    
    PRIMARY KEY (user_id, book_id)
);

-- Helpful indexes for user_books
CREATE INDEX IF NOT EXISTS idx_user_books_user ON user_books (user_id);
CREATE INDEX IF NOT EXISTS idx_user_books_book ON user_books (book_id);

-- Helpful index for books
CREATE INDEX IF NOT EXISTS idx_books_language_level ON books (language_code, level);

-- ==========================================
-- VOCABULARY: tracked words with translation
-- ==========================================
CREATE TABLE IF NOT EXISTS vocabulary (
    id              BIGSERIAL PRIMARY KEY,
    
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id         BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    
    -- language of the word (usually the target language of the book)
    language_code   VARCHAR(10) NOT NULL,      -- e.g. 'en', 'fr', 'es'
    
    word            TEXT NOT NULL,             -- the original word/token
    translation     TEXT NOT NULL,             -- translated word/phrase
    
    -- optional stats (based on interactive reading behaviour)
    hover_count     INT NOT NULL DEFAULT 0,    -- how many times user hovered it
    last_seen_at    TIMESTAMPTZ,               -- timestamp of last hover/view
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (user_id, book_id, language_code, word)
);

-- Helpful indexes for vocabulary
CREATE INDEX IF NOT EXISTS idx_vocab_user ON vocabulary (user_id);
CREATE INDEX IF NOT EXISTS idx_vocab_book ON vocabulary (book_id);
CREATE INDEX IF NOT EXISTS idx_vocab_user_book ON vocabulary (user_id, book_id);
CREATE INDEX IF NOT EXISTS idx_vocab_lang_word ON vocabulary (language_code, word);

-- Insert some test data (optional)
-- Uncomment for development/testing
/*
INSERT INTO users (email, display_name) VALUES 
    ('test@example.com', 'Test User')
ON CONFLICT (email) DO NOTHING;
*/

