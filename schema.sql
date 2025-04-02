CREATE TABLE IF NOT EXISTS log (
    id BIGSERIAL PRIMARY KEY,
    android_token VARCHAR(100) DEFAULT NULL,
    android_package VARCHAR(100) DEFAULT NULL,
    protocol VARCHAR(10) NOT NULL DEFAULT 'http',
    subdomain VARCHAR(100) DEFAULT NULL,
    domain VARCHAR(100) DEFAULT NULL,
    tld VARCHAR(100) DEFAULT NULL,
    port SMALLINT DEFAULT NULL,
    path VARCHAR(1000) DEFAULT NULL,
    path_etc VARCHAR(1000) DEFAULT NULL,
    query VARCHAR(1000) DEFAULT NULL,
    fragment VARCHAR(1000) DEFAULT NULL,
    username VARCHAR(100) DEFAULT NULL,
    password VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Temel indeksler
CREATE INDEX IF NOT EXISTS log_created_at_idx ON log (created_at);
CREATE INDEX IF NOT EXISTS log_subdomain_idx ON log (subdomain);
CREATE INDEX IF NOT EXISTS log_domain_idx ON log (domain);
CREATE INDEX IF NOT EXISTS log_path_idx ON log (path);
CREATE INDEX IF NOT EXISTS log_query_idx ON log (query);
CREATE INDEX IF NOT EXISTS log_fragment_idx ON log (fragment);
CREATE INDEX IF NOT EXISTS log_protocol_idx ON log (protocol);
CREATE INDEX IF NOT EXISTS log_port_idx ON log (port);
CREATE INDEX IF NOT EXISTS log_username_idx ON log (username);
CREATE INDEX IF NOT EXISTS log_password_idx ON log (password);
CREATE INDEX IF NOT EXISTS log_tld_idx ON log (tld);
CREATE INDEX IF NOT EXISTS log_path_etc_idx ON log (path_etc);

-- Android özel indeksler
CREATE INDEX IF NOT EXISTS log_android_token_idx ON log (android_token);
CREATE INDEX IF NOT EXISTS log_android_package_idx ON log (android_package);
CREATE INDEX IF NOT EXISTS log_android_combined_idx ON log (android_token, android_package);

-- Çoklu alan indeksleri
CREATE INDEX IF NOT EXISTS log_subdomain_domain_idx ON log (subdomain, domain);
CREATE INDEX IF NOT EXISTS log_domain_tld_idx ON log (domain, tld);
CREATE INDEX IF NOT EXISTS log_subdomain_domain_tld_idx ON log (subdomain, domain, tld);
CREATE INDEX IF NOT EXISTS log_subdomain_domain_path_idx ON log (subdomain, domain, path);
CREATE INDEX IF NOT EXISTS log_subdomain_domain_path_query_idx ON log (subdomain, domain, path, query);
CREATE INDEX IF NOT EXISTS log_subdomain_domain_path_query_fragment_idx ON log (subdomain, domain, path, query, fragment);
CREATE INDEX IF NOT EXISTS log_subdomain_domain_path_query_fragment_protocol_idx ON log (subdomain, domain, path, query, fragment, protocol);
CREATE INDEX IF NOT EXISTS log_subdomain_domain_path_query_fragment_protocol_port_idx ON log (subdomain, domain, path, query, fragment, protocol, port);
CREATE INDEX IF NOT EXISTS log_subdomain_domain_path_query_fragment_protocol_port_cr_idx ON log (subdomain, domain, path, query, fragment, protocol, port, created_at);

-- Kimlik bilgileri indeksleri
CREATE INDEX IF NOT EXISTS log_username_password_idx ON log (username, password);
CREATE INDEX IF NOT EXISTS log_username_domain_idx ON log (username, domain);
CREATE INDEX IF NOT EXISTS log_password_domain_idx ON log (password, domain);

-- Protokol bazlı indeksler
CREATE INDEX IF NOT EXISTS log_protocol_domain_idx ON log (protocol, domain);
CREATE INDEX IF NOT EXISTS log_protocol_port_idx ON log (protocol, port);
CREATE INDEX IF NOT EXISTS log_protocol_subdomain_domain_idx ON log (protocol, subdomain, domain);

-- Zaman bazlı indeksler
CREATE INDEX IF NOT EXISTS log_created_at_domain_idx ON log (created_at, domain);
CREATE INDEX IF NOT EXISTS log_created_at_protocol_idx ON log (created_at, protocol);
CREATE INDEX IF NOT EXISTS log_created_at_android_token_idx ON log (created_at, android_token);
CREATE INDEX IF NOT EXISTS log_created_at_android_package_idx ON log (created_at, android_package);

-- Path ve path_etc indeksleri
CREATE INDEX IF NOT EXISTS log_path_path_etc_idx ON log (path, path_etc);

-- LIKE sorguları için GIN indeksleri (PostgreSQL)
-- Önce pg_trgm extension'ı yüklenmeli
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS log_domain_gin_idx ON log USING gin (domain gin_trgm_ops);
CREATE INDEX IF NOT EXISTS log_path_gin_idx ON log USING gin (path gin_trgm_ops);
CREATE INDEX IF NOT EXISTS log_subdomain_gin_idx ON log USING gin (subdomain gin_trgm_ops);
CREATE INDEX IF NOT EXISTS log_query_gin_idx ON log USING gin (query gin_trgm_ops);
CREATE INDEX IF NOT EXISTS log_path_etc_gin_idx ON log USING gin (path_etc gin_trgm_ops);
CREATE INDEX IF NOT EXISTS log_android_token_gin_idx ON log USING gin (android_token gin_trgm_ops);
CREATE INDEX IF NOT EXISTS log_android_package_gin_idx ON log USING gin (android_package gin_trgm_ops);

-- Partial indeksler (NULL olmayan değerler için)
CREATE INDEX IF NOT EXISTS log_username_not_null_idx ON log (username) WHERE username IS NOT NULL;
CREATE INDEX IF NOT EXISTS log_password_not_null_idx ON log (password) WHERE password IS NOT NULL;
CREATE INDEX IF NOT EXISTS log_android_token_not_null_idx ON log (android_token) WHERE android_token IS NOT NULL;
