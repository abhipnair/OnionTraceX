-- =====================================
-- 1️⃣ KEYWORDS TABLE
-- =====================================
CREATE TABLE IF NOT EXISTS Keywords (
    keyword_id CHAR(64) PRIMARY KEY,          -- SHA-256(keyword)
    keyword TEXT NOT NULL,
    date_added TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================
-- 2️⃣ ONION SITES (MASTER TABLE)
-- =====================================
CREATE TABLE IF NOT EXISTS OnionSites (
    site_id CHAR(64) PRIMARY KEY,             -- SHA-256(onion URL)
    url TEXT NOT NULL,
    source TEXT NOT NULL,                     -- Keyword / Custom / Exploratory
    keyword TEXT,
    current_status TEXT NOT NULL,             -- Alive / Dead / Timeout
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================
-- 3️⃣ SITE LIVENESS HISTORY
-- =====================================
CREATE TABLE IF NOT EXISTS SiteLiveness (
    liveness_id CHAR(64) PRIMARY KEY,         -- SHA-256(site_id + timestamp)
    site_id CHAR(64) REFERENCES OnionSites(site_id) ON DELETE CASCADE,
    status TEXT NOT NULL,                     -- Alive / Dead / Timeout
    response_time FLOAT,
    check_time TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================
-- 4️⃣ PAGES (HTML CONTENT STORAGE)
-- =====================================
CREATE TABLE IF NOT EXISTS Pages (
    page_id CHAR(64) PRIMARY KEY,             -- SHA-256(page URL)
    site_id CHAR(64) REFERENCES OnionSites(site_id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    html_hash CHAR(64),
    raw_html BYTEA,
    crawl_date TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================
-- 5️⃣ METADATA (EXTRACTED FIELDS)
-- =====================================
CREATE TABLE IF NOT EXISTS Metadata (
    metadata_id CHAR(64) PRIMARY KEY,         -- SHA-256(page_id + timestamp)
    page_id CHAR(64) REFERENCES Pages(page_id) ON DELETE CASCADE,
    title TEXT,
    meta_tags JSONB,
    emails JSONB,
    pgp_keys JSONB,
    language TEXT,
    translated_text TEXT
);

-- =====================================
-- 6️⃣ BITCOIN ADDRESSES
-- =====================================
CREATE TABLE IF NOT EXISTS BitcoinAddresses (
    address_id CHAR(64) PRIMARY KEY,          -- SHA-256(BTC address)
    address TEXT NOT NULL UNIQUE,
    site_id CHAR(64) REFERENCES OnionSites(site_id) ON DELETE CASCADE,
    page_id CHAR(64) REFERENCES Pages(page_id) ON DELETE CASCADE,
    valid BOOLEAN DEFAULT FALSE,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================
-- 7️⃣ TRANSACTIONS
-- =====================================
CREATE TABLE IF NOT EXISTS Transactions (
    tx_id CHAR(64) PRIMARY KEY,               -- Blockchain transaction hash
    address_id CHAR(64) REFERENCES BitcoinAddresses(address_id) ON DELETE CASCADE,
    direction TEXT,                           -- Inbound / Outbound
    amount FLOAT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    fan_in INT,
    fan_out INT
);

-- =====================================
-- 8️⃣ CLASSIFICATION (AI/NLP RESULTS)
-- =====================================
CREATE TABLE IF NOT EXISTS Classification (
    class_id CHAR(64) PRIMARY KEY,            -- SHA-256(page_id + category)
    page_id CHAR(64) REFERENCES Pages(page_id) ON DELETE CASCADE,
    category TEXT,
    confidence FLOAT CHECK (confidence BETWEEN 0 AND 1)
);

-- =====================================
-- 9️⃣ VENDOR PROFILES (CLUSTERS)
-- =====================================
CREATE TABLE IF NOT EXISTS VendorProfiles (
    vendor_id CHAR(64) PRIMARY KEY,           -- SHA-256(cluster signature)
    onion_ids JSONB,
    similarity_score FLOAT CHECK (similarity_score BETWEEN 0 AND 1),
    evidence JSONB
);

-- =====================================
-- 🔟 REPORTS (CHAIN OF CUSTODY / EVIDENCE)
-- =====================================
CREATE TABLE IF NOT EXISTS Reports (
    report_id CHAR(64) PRIMARY KEY,           -- SHA-256(report file)
    site_id CHAR(64) REFERENCES OnionSites(site_id) ON DELETE CASCADE,
    report_hash CHAR(64),
    report_file BYTEA,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================
-- ⚡ PERFORMANCE INDEXES
-- =====================================
CREATE INDEX IF NOT EXISTS idx_onionsites_url ON OnionSites (url);
CREATE INDEX IF NOT EXISTS idx_pages_site_id ON Pages (site_id);
CREATE INDEX IF NOT EXISTS idx_metadata_page_id ON Metadata (page_id);
CREATE INDEX IF NOT EXISTS idx_bitcoin_site_id ON BitcoinAddresses (site_id);
CREATE INDEX IF NOT EXISTS idx_tx_address_id ON Transactions (address_id);
CREATE INDEX IF NOT EXISTS idx_class_page_id ON Classification (page_id);
CREATE INDEX IF NOT EXISTS idx_liveness_site_id ON SiteLiveness (site_id);

-- =====================================
-- 🔄 AUTO UPDATE last_seen WHEN STATUS CHANGES
-- =====================================
CREATE OR REPLACE FUNCTION update_last_seen()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_seen = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_last_seen
BEFORE UPDATE ON OnionSites
FOR EACH ROW
EXECUTE FUNCTION update_last_seen();
