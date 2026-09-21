CREATE TABLE IF NOT EXISTS case_transactions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  case_id VARCHAR(32) NOT NULL,
  transaction_type VARCHAR(32) NOT NULL,
  transaction_at DATETIME(6) NOT NULL,
  amount DECIMAL(19,2) NOT NULL,
  account_number VARCHAR(100) NULL,
  counterparty_name VARCHAR(100) NULL,
  counterparty_account VARCHAR(100) NULL,
  bank_name VARCHAR(100) NULL,
  memo VARCHAR(500) NULL,
  source VARCHAR(32) NOT NULL DEFAULT 'MANUAL',
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY idx_case_transactions_case_at (case_id, transaction_at),
  CONSTRAINT fk_case_transactions_case FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
