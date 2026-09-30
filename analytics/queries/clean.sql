-- Build clean_events from raw_events.
--
-- 1. Drop exact duplicate deliveries (same event_id sent twice by a client retry).
-- 2. Drop event names we don't recognize.
-- 3. Drop events stamped before the player's install (bad device clocks).

DROP TABLE IF EXISTS clean_events;

CREATE TABLE clean_events AS
WITH deduped AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY rowid) AS copy_no
    FROM raw_events
),
known AS (
    SELECT event_id, player_id, event, ts, variant
    FROM deduped
    WHERE copy_no = 1
      AND event IN ('install', 'session_start', 'tutorial_start',
                    'tutorial_complete', 'first_match', 'first_purchase')
),
installs AS (
    SELECT player_id, MIN(ts) AS installed_at
    FROM known
    WHERE event = 'install'
    GROUP BY player_id
)
SELECT k.*
FROM known k
JOIN installs i ON i.player_id = k.player_id
WHERE k.ts >= i.installed_at;

CREATE INDEX idx_clean_player_event ON clean_events (player_id, event, ts);

DROP TABLE IF EXISTS players;

CREATE TABLE players AS
SELECT player_id,
       MIN(ts)       AS installed_at,
       date(MIN(ts)) AS install_day,
       MAX(variant)  AS variant
FROM clean_events
WHERE event = 'install'
GROUP BY player_id;
