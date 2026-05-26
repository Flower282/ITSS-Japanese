-- Run once if demo.message.is_marked does not exist yet (see ITSS_Nhat_Database.pdf).
-- Replace demo with your SCHEMA_NAME from .env if different.

ALTER TABLE demo.message
    ADD COLUMN IF NOT EXISTS is_marked SMALLINT NOT NULL DEFAULT 0;
