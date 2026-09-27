-- Inicialização do banco do OpenMetadata (RF27)
SELECT 'CREATE DATABASE openmetadata_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'openmetadata_db')\gexec
