-- The application migration owns extension creation. Initialization only proves that
-- the pinned database runtime exposes the expected PostGIS extension line.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_available_extensions
        WHERE name = 'postgis' AND default_version LIKE '3.5.%'
    ) THEN
        RAISE EXCEPTION 'PostGIS 3.5.x is not available in the database runtime';
    END IF;
END
$$;
