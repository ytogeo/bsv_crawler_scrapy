CREATE TABLE IF NOT EXISTS crawl_job (
  id VARCHAR(64) PRIMARY KEY,
  status VARCHAR(32) NOT NULL,
  config_path VARCHAR(512) NOT NULL,
  started_at DATETIME NOT NULL,
  finished_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS seed_task (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  job_id VARCHAR(64) NOT NULL,
  point_index INT NOT NULL,
  lng DOUBLE NOT NULL,
  lat DOUBLE NOT NULL,
  status VARCHAR(32) NOT NULL,
  panoid VARCHAR(128) NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_seed_task_job_point (job_id, point_index),
  KEY idx_seed_task_job_status (job_id, status),
  KEY idx_seed_task_job_panoid (job_id, panoid)
);

CREATE TABLE IF NOT EXISTS pano (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  job_id VARCHAR(64) NOT NULL,
  panoid VARCHAR(128) NOT NULL,
  source_point_index INT NULL,
  source_lng DOUBLE NULL,
  source_lat DOUBLE NULL,
  pano_lng DOUBLE NULL,
  pano_lat DOUBLE NULL,
  capture_date VARCHAR(64) NULL,
  provider VARCHAR(64) NOT NULL,
  raw_json JSON NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_pano_job_panoid (job_id, panoid),
  KEY idx_pano_job (job_id),
  KEY idx_pano_provider (provider)
);

CREATE TABLE IF NOT EXISTS pano_asset (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  job_id VARCHAR(64) NOT NULL,
  panoid VARCHAR(128) NOT NULL,
  asset_type VARCHAR(64) NOT NULL,
  asset_spec VARCHAR(128) NOT NULL,
  file_path VARCHAR(1024) NULL,
  file_size_bytes BIGINT NULL,
  width INT NULL,
  height INT NULL,
  sha256 CHAR(64) NULL,
  status VARCHAR(32) NOT NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_asset_job_panoid_type_spec (job_id, panoid, asset_type, asset_spec),
  KEY idx_asset_job_status (job_id, status),
  KEY idx_asset_sha256 (sha256)
);

CREATE TABLE IF NOT EXISTS crawl_error (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  job_id VARCHAR(64) NOT NULL,
  stage VARCHAR(64) NOT NULL,
  url TEXT NULL,
  point_index INT NULL,
  panoid VARCHAR(128) NULL,
  error_type VARCHAR(128) NOT NULL,
  error_message TEXT NOT NULL,
  context_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_error_job_stage (job_id, stage),
  KEY idx_error_job_panoid (job_id, panoid)
);

