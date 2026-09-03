-- ============================================================
-- schema-h2.sql : embedded H2 schema (zero external dependency)
-- Author: [Name]  Student ID: [ID]  2026-07
-- H2 runs in MySQL compatibility mode (MODE=MySQL);
-- compatible with the MySQL version sql/init.sql.
-- ============================================================
CREATE TABLE IF NOT EXISTS t_user (
  id          BIGINT       NOT NULL AUTO_INCREMENT,
  username    VARCHAR(50)  NOT NULL,
  password    VARCHAR(100) NOT NULL,
  nickname    VARCHAR(50)  DEFAULT NULL,
  role        VARCHAR(10)  NOT NULL DEFAULT 'USER',
  create_time TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_username ON t_user (username);

CREATE TABLE IF NOT EXISTS t_task (
  id          BIGINT       NOT NULL AUTO_INCREMENT,
  user_id     BIGINT       NOT NULL,
  media_type  VARCHAR(10)  NOT NULL DEFAULT 'VIDEO',
  file_name   VARCHAR(255) DEFAULT NULL,
  file_path   VARCHAR(500) DEFAULT NULL,
  bbox        VARCHAR(50)  DEFAULT NULL,
  status      VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
  result_path VARCHAR(500) DEFAULT NULL,
  log_path    VARCHAR(500) DEFAULT NULL,
  stats_json  CLOB         DEFAULT NULL,
  error_msg   VARCHAR(500) DEFAULT NULL,
  create_time TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finish_time TIMESTAMP    DEFAULT NULL,
  PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_user ON t_task (user_id);
CREATE INDEX IF NOT EXISTS idx_status ON t_task (status);
