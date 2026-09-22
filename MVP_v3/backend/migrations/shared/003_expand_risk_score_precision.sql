ALTER TABLE cases
    MODIFY risk_score DECIMAL(9, 6) NOT NULL;

ALTER TABLE analysis_segments
    MODIFY risk_score DECIMAL(9, 6) NOT NULL;
