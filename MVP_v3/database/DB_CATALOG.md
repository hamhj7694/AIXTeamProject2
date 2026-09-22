{
  "database": "csr",
  "inspected_at_utc": "2026-09-22T02:27:14.090497+00:00",
  "schema": {
    "tables": {
      "actions": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "action_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "action_type": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "title": {
            "COLUMN_TYPE": "varchar(300)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "REQUESTED",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "actor_type": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "version": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "note": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_by": {
            "COLUMN_TYPE": "varchar(128)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "visibility": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "BANK_INTERNAL",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_actions_case_cursor": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "created_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "action_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "action_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_actions_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {
          "chk_actions_version": {
            "clause": "(version>=1)",
            "enforced": "YES"
          },
          "chk_actions_visibility": {
            "clause": "(visibilityin(_utf8mb4\\'BANK_INTERNAL\\',_utf8mb4\\'CUSTOMER_SHARED\\'))",
            "enforced": "YES"
          }
        }
      },
      "analysis_segments": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "segment_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "start_turn": {
            "COLUMN_TYPE": "int",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "end_turn": {
            "COLUMN_TYPE": "int",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "segment_text": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "risk_score": {
            "COLUMN_TYPE": "decimal(9,6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "model_label": {
            "COLUMN_TYPE": "enum('NORMAL','PHISHING')",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "evidence_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "fk_segments_case": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "segment_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_segments_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "bank_staff_directory": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "staff_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "display_name": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "assignment_role": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CONSULTATION",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "role_label": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "position_title": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status_text": {
            "COLUMN_TYPE": "varchar(80)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "근무 중",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status_color_key": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "GREEN",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "assignment_eligible": {
            "COLUMN_TYPE": "tinyint(1)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "linked_user_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "deleted_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_bank_staff_active": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "deleted_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "display_name",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "staff_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {},
        "checks": {
          "chk_bank_staff_color": {
            "clause": "(status_color_keyin(_utf8mb4\\'GREEN\\',_utf8mb4\\'BLUE\\',_utf8mb4\\'YELLOW\\',_utf8mb4\\'ORANGE\\',_utf8mb4\\'RED\\',_utf8mb4\\'PURPLE\\',_utf8mb4\\'GRAY\\'))",
            "enforced": "YES"
          },
          "chk_bank_staff_assignment_role": {
            "clause": "(assignment_rolein(_utf8mb4\\'SUPERVISOR\\',_utf8mb4\\'MONITORING\\',_utf8mb4\\'CONSULTATION\\',_utf8mb4\\'OTHER_VIEWER\\',_utf8mb4\\'HANDOVER_PENDING\\'))",
            "enforced": "YES"
          }
        }
      },
      "case_ai_suggestions": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "suggestion_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "suggestion_type": {
            "COLUMN_TYPE": "varchar(40)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "title": {
            "COLUMN_TYPE": "varchar(300)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "rationale": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "priority": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "PROPOSED",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "related_gap_ids_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "evidence_refs_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "dedupe_key": {
            "COLUMN_TYPE": "varchar(255)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_bin",
            "GENERATION_EXPRESSION": ""
          },
          "execution_mode": {
            "COLUMN_TYPE": "varchar(40)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "HUMAN_REVIEW_REQUIRED",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "source_revision": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "model_version": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "prompt_version": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "accepted_task_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "reviewed_by": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "reviewed_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "dismissal_reason": {
            "COLUMN_TYPE": "varchar(1000)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "version": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "active_dedupe_key": {
            "COLUMN_TYPE": "varchar(255)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "STORED GENERATED",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_bin",
            "GENERATION_EXPRESSION": "(case when (`status` = _utf8mb4\\'PROPOSED\\') then `dedupe_key` else NULL end)"
          }
        },
        "indexes": {
          "idx_ai_suggestions_state": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "status",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "priority",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "suggestion_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_ai_suggestion_active": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "active_dedupe_key",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_ai_suggestion_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ]
        },
        "checks": {
          "chk_ai_suggestion_type": {
            "clause": "(suggestion_typein(_utf8mb4\\'CUSTOMER_QUESTION\\',_utf8mb4\\'INSTITUTION_VERIFICATION\\',_utf8mb4\\'TRANSACTION_REVIEW\\',_utf8mb4\\'PROTECTIVE_ACTION\\',_utf8mb4\\'DOCUMENT_REQUEST\\',_utf8mb4\\'STAFF_REVIEW\\'))",
            "enforced": "YES"
          },
          "chk_ai_suggestion_priority": {
            "clause": "(priorityin(_utf8mb4\\'URGENT\\',_utf8mb4\\'HIGH\\',_utf8mb4\\'NORMAL\\'))",
            "enforced": "YES"
          },
          "chk_ai_suggestion_status": {
            "clause": "(statusin(_utf8mb4\\'PROPOSED\\',_utf8mb4\\'ACCEPTED\\',_utf8mb4\\'DISMISSED\\',_utf8mb4\\'EXPIRED\\',_utf8mb4\\'SUPERSEDED\\'))",
            "enforced": "YES"
          },
          "chk_ai_suggestion_mode": {
            "clause": "(execution_modein(_utf8mb4\\'HUMAN_REVIEW_REQUIRED\\',_utf8mb4\\'AUTO_CUSTOMER_QUESTION_ALLOWED\\'))",
            "enforced": "YES"
          },
          "chk_ai_suggestion_review": {
            "clause": "((statusnotin(_utf8mb4\\'ACCEPTED\\',_utf8mb4\\'DISMISSED\\'))or((reviewed_byisnotnull)and(reviewed_atisnotnull)))",
            "enforced": "YES"
          },
          "chk_ai_suggestion_dismissed": {
            "clause": "((status<>_utf8mb4\\'DISMISSED\\')or(dismissal_reasonisnotnull))",
            "enforced": "YES"
          }
        }
      },
      "case_context_facts_v2": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "fact_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "semantic_key": {
            "COLUMN_TYPE": "varchar(160)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_bin",
            "GENERATION_EXPRESSION": ""
          },
          "display_label": {
            "COLUMN_TYPE": "varchar(255)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "value_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "display_value": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "source_kind": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "PROPOSED",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "confidence": {
            "COLUMN_TYPE": "decimal(5,4)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "evidence_refs_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "visibility": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "BANK_INTERNAL",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "confirmed_by": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "confirmed_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "rejection_reason": {
            "COLUMN_TYPE": "varchar(1000)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "supersedes_fact_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "client_request_id": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "version": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "fk_context_fact_v2_supersedes": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "supersedes_fact_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "idx_context_facts_case_state": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "status",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "semantic_key",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "fact_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_context_fact_request": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "client_request_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_context_fact_v2_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ],
          "fk_context_fact_v2_supersedes": [
            {
              "COLUMN_NAME": "supersedes_fact_id",
              "REFERENCED_TABLE_NAME": "case_context_facts_v2",
              "REFERENCED_COLUMN_NAME": "fact_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "SET NULL"
            }
          ]
        },
        "checks": {
          "chk_context_fact_status": {
            "clause": "(statusin(_utf8mb4\\'PROPOSED\\',_utf8mb4\\'CONFIRMED\\',_utf8mb4\\'REJECTED\\',_utf8mb4\\'SUPERSEDED\\'))",
            "enforced": "YES"
          },
          "chk_context_fact_source": {
            "clause": "(source_kindin(_utf8mb4\\'AI_EXTRACTION\\',_utf8mb4\\'CUSTOMER_STATEMENT\\',_utf8mb4\\'STAFF_OBSERVATION\\',_utf8mb4\\'BANK_RECORD\\',_utf8mb4\\'OFFICIAL_VERIFICATION\\'))",
            "enforced": "YES"
          },
          "chk_context_fact_visibility": {
            "clause": "(visibilityin(_utf8mb4\\'BANK_INTERNAL\\',_utf8mb4\\'CUSTOMER_SHARED\\'))",
            "enforced": "YES"
          },
          "chk_context_fact_confidence": {
            "clause": "((confidenceisnull)or((confidence>=0)and(confidence<=1)))",
            "enforced": "YES"
          },
          "chk_context_fact_confirmed": {
            "clause": "((status<>_utf8mb4\\'CONFIRMED\\')or((confirmed_byisnotnull)and(confirmed_atisnotnull)))",
            "enforced": "YES"
          },
          "chk_context_fact_rejected": {
            "clause": "((status<>_utf8mb4\\'REJECTED\\')or(rejection_reasonisnotnull))",
            "enforced": "YES"
          }
        }
      },
      "case_context_item_history": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "history_id": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "auto_increment",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "item_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "item_version": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "operation": {
            "COLUMN_TYPE": "varchar(24)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "actor_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "before_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "after_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "history_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_context_history_version": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "item_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "item_version",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_context_history_item": [
            {
              "COLUMN_NAME": "item_id",
              "REFERENCED_TABLE_NAME": "case_context_items",
              "REFERENCED_COLUMN_NAME": "item_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "case_context_items": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "item_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "section": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "semantic_key": {
            "COLUMN_TYPE": "varchar(160)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_bin",
            "GENERATION_EXPRESSION": ""
          },
          "item_version": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "state_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "item_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_context_semantic": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "section",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "semantic_key",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_context_item_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "case_context_observations": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "observation_id": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "observation_type": {
            "COLUMN_TYPE": "varchar(80)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "payload_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "status": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "UNMAPPED",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "created_by": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_context_observations_review": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "status",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "created_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "observation_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_context_observations_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ]
        },
        "checks": {
          "chk_context_observations_status": {
            "clause": "(statusin(_utf8mb4\\'UNMAPPED\\',_utf8mb4\\'REVIEWED\\',_utf8mb4\\'MAPPED\\',_utf8mb4\\'DISMISSED\\'))",
            "enforced": "YES"
          }
        }
      },
      "case_context_projections": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "generation_status": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "EMPTY",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "generating_revision": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "lease_token": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "lease_expires_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "last_success_revision": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "last_success_payload": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "schema_version": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "case-support.v1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "model_version": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "prompt_version": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "last_error": {
            "COLUMN_TYPE": "varchar(500)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "generated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_context_projection_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "case_context_signals": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "signal_id": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "signal_code": {
            "COLUMN_TYPE": "varchar(120)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "severity": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "confidence": {
            "COLUMN_TYPE": "decimal(5,4)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "claim_status": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "visibility": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "BANK_INTERNAL",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "payload_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "source_revision": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_case_signals_state": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "severity",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "visibility",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "signal_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_case_signals_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ]
        },
        "checks": {
          "chk_case_signal_confidence": {
            "clause": "((confidence>=0)and(confidence<=1))",
            "enforced": "YES"
          },
          "chk_case_signal_visibility": {
            "clause": "(visibilityin(_utf8mb4\\'BANK_INTERNAL\\',_utf8mb4\\'CUSTOMER_SHARED\\',_utf8mb4\\'SHARED\\'))",
            "enforced": "YES"
          }
        }
      },
      "case_context_v2_history": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "history_id": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "auto_increment",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "entity_type": {
            "COLUMN_TYPE": "varchar(24)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "entity_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "entity_version": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "operation": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "actor_user_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "before_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "after_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_context_v2_history_case": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "created_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "history_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_context_v2_history_version": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "entity_type",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "entity_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "entity_version",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_context_v2_history_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ]
        },
        "checks": {}
      },
      "case_decisions": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "decision_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "decision_type": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "title": {
            "COLUMN_TYPE": "varchar(300)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "rationale": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "related_entity_type": {
            "COLUMN_TYPE": "varchar(24)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "related_entity_id": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "visibility": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "BANK_INTERNAL",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "actor_user_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "supersedes_decision_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "client_request_id": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "fk_case_decision_supersedes": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "supersedes_decision_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "idx_case_decisions_created": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "created_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "decision_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "decision_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_case_decision_request": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "client_request_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_case_decision_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ],
          "fk_case_decision_supersedes": [
            {
              "COLUMN_NAME": "supersedes_decision_id",
              "REFERENCED_TABLE_NAME": "case_decisions",
              "REFERENCED_COLUMN_NAME": "decision_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "SET NULL"
            }
          ]
        },
        "checks": {
          "chk_case_decision_type": {
            "clause": "(decision_typein(_utf8mb4\\'FACT_REVIEW\\',_utf8mb4\\'TASK_DECISION\\',_utf8mb4\\'CASE_STATUS\\',_utf8mb4\\'CUSTOMER_DISCLOSURE\\',_utf8mb4\\'OTHER\\'))",
            "enforced": "YES"
          },
          "chk_case_decision_entity": {
            "clause": "(related_entity_typein(_utf8mb4\\'FACT\\',_utf8mb4\\'GAP\\',_utf8mb4\\'SUGGESTION\\',_utf8mb4\\'TASK\\',_utf8mb4\\'VERIFICATION\\',_utf8mb4\\'CASE\\'))",
            "enforced": "YES"
          },
          "chk_case_decision_visibility": {
            "clause": "(visibilityin(_utf8mb4\\'BANK_INTERNAL\\',_utf8mb4\\'CUSTOMER_SHARED\\'))",
            "enforced": "YES"
          }
        }
      },
      "case_events": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "event_id": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "auto_increment",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "event_type": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "actor_type": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "SYSTEM",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "payload_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "occurred_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_case_events_case_cursor": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "event_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "event_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_case_events_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "case_gaps": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "gap_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "semantic_key": {
            "COLUMN_TYPE": "varchar(160)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_bin",
            "GENERATION_EXPRESSION": ""
          },
          "title": {
            "COLUMN_TYPE": "varchar(300)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "reason": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "priority": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "OPEN",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "source": {
            "COLUMN_TYPE": "varchar(24)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "evidence_refs_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "related_question_ids_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "related_verification_ids_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "resolution_fact_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "dismissal_reason": {
            "COLUMN_TYPE": "varchar(1000)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "visibility": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "BANK_INTERNAL",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "source_revision": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "client_request_id": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "version": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "active_semantic_key": {
            "COLUMN_TYPE": "varchar(160)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "STORED GENERATED",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_bin",
            "GENERATION_EXPRESSION": "(case when (`status` in (_utf8mb4\\'OPEN\\',_utf8mb4\\'AWAITING_CUSTOMER\\',_utf8mb4\\'AWAITING_INSTITUTION\\',_utf8mb4\\'STAFF_REVIEW_REQUIRED\\')) then `semantic_key` else NULL end)"
          }
        },
        "indexes": {
          "fk_case_gap_resolution": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "resolution_fact_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "idx_case_gaps_state": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "status",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "priority",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "gap_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_case_gap_active": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "active_semantic_key",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_case_gap_request": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "client_request_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_case_gap_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ],
          "fk_case_gap_resolution": [
            {
              "COLUMN_NAME": "resolution_fact_id",
              "REFERENCED_TABLE_NAME": "case_context_facts_v2",
              "REFERENCED_COLUMN_NAME": "fact_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "RESTRICT"
            }
          ]
        },
        "checks": {
          "chk_case_gap_status": {
            "clause": "(statusin(_utf8mb4\\'OPEN\\',_utf8mb4\\'AWAITING_CUSTOMER\\',_utf8mb4\\'AWAITING_INSTITUTION\\',_utf8mb4\\'STAFF_REVIEW_REQUIRED\\',_utf8mb4\\'RESOLVED\\',_utf8mb4\\'DISMISSED\\'))",
            "enforced": "YES"
          },
          "chk_case_gap_priority": {
            "clause": "(priorityin(_utf8mb4\\'URGENT\\',_utf8mb4\\'HIGH\\',_utf8mb4\\'NORMAL\\'))",
            "enforced": "YES"
          },
          "chk_case_gap_source": {
            "clause": "(sourcein(_utf8mb4\\'AI\\',_utf8mb4\\'BANK_STAFF\\',_utf8mb4\\'SYSTEM_RULE\\'))",
            "enforced": "YES"
          },
          "chk_case_gap_visibility": {
            "clause": "(visibility=_utf8mb4\\'BANK_INTERNAL\\')",
            "enforced": "YES"
          },
          "chk_case_gap_resolved": {
            "clause": "((status<>_utf8mb4\\'RESOLVED\\')or(resolution_fact_idisnotnull))",
            "enforced": "YES"
          },
          "chk_case_gap_dismissed": {
            "clause": "((status<>_utf8mb4\\'DISMISSED\\')or(dismissal_reasonisnotnull))",
            "enforced": "YES"
          }
        }
      },
      "case_inputs": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "input_id": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "auto_increment",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "input_type": {
            "COLUMN_TYPE": "enum('TEXT','VOICE_TRANSCRIPT')",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "TEXT",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "input_text": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "fk_case_inputs_case": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "input_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_case_inputs_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "case_members": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "user_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "display_name": {
            "COLUMN_TYPE": "varchar(80)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "role": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "assignment_role": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "HANDOVER_PENDING",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "ACTIVE",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "assigned_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "user_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_case_members_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {
          "chk_case_member_assignment_role": {
            "clause": "(assignment_rolein(_utf8mb4\\'SUPERVISOR\\',_utf8mb4\\'MONITORING\\',_utf8mb4\\'CONSULTATION\\',_utf8mb4\\'VIEWER\\',_utf8mb4\\'HANDOVER_PENDING\\'))",
            "enforced": "YES"
          }
        }
      },
      "case_presence": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "user_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "display_name": {
            "COLUMN_TYPE": "varchar(80)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "presence": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "channel": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "last_seen_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "expires_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_case_presence_expiry": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "expires_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "user_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_case_presence_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "case_report_sections": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "report_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "section_key": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "content_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "section_version": {
            "COLUMN_TYPE": "int",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "report_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "section_key",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_report_sections_report": [
            {
              "COLUMN_NAME": "report_id",
              "REFERENCED_TABLE_NAME": "case_reports",
              "REFERENCED_COLUMN_NAME": "report_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "case_reports": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "report_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "report_type": {
            "COLUMN_TYPE": "enum('LIVE','FINAL')",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "LIVE",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "report_version": {
            "COLUMN_TYPE": "int",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "report_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_case_live_report": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "report_type",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_case_reports_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "case_semantic_atoms": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "atom_id": {
            "COLUMN_TYPE": "varchar(80)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "atom_class": {
            "COLUMN_TYPE": "varchar(80)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "predicate": {
            "COLUMN_TYPE": "varchar(120)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "source_turn_id": {
            "COLUMN_TYPE": "int",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "semantic_fingerprint": {
            "COLUMN_TYPE": "varchar(128)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "payload_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "source_revision": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_case_atoms_turn": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "source_turn_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "atom_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_case_atom_fingerprint": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "semantic_fingerprint",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_case_atoms_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ]
        },
        "checks": {}
      },
      "case_semantic_relations": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "relation_id": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "relation_type": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "source_atom_id": {
            "COLUMN_TYPE": "varchar(80)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "target_atom_id": {
            "COLUMN_TYPE": "varchar(80)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "confidence": {
            "COLUMN_TYPE": "decimal(5,4)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "payload_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "source_revision": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_case_relations_atoms": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "source_atom_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "target_atom_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "relation_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_case_relations_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ]
        },
        "checks": {
          "chk_case_relation_confidence": {
            "clause": "((confidence>=0)and(confidence<=1))",
            "enforced": "YES"
          }
        }
      },
      "case_tasks": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "task_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "source": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "source_suggestion_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "task_type": {
            "COLUMN_TYPE": "varchar(40)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "title": {
            "COLUMN_TYPE": "varchar(300)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "description": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "priority": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "TODO",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "assignee_user_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "due_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "related_gap_ids_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "related_verification_ids_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "result_code": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "result_summary": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "evidence_refs_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "customer_visibility": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "INTERNAL_ONLY",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "completed_by": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "completed_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "cancellation_reason": {
            "COLUMN_TYPE": "varchar(1000)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "client_request_id": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "version": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_by": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "fk_case_task_suggestion": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "source_suggestion_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "idx_case_tasks_assignee": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "assignee_user_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "status",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "idx_case_tasks_state": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "status",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "priority",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "updated_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "task_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_case_task_request": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "client_request_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_case_task_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ],
          "fk_case_task_suggestion": [
            {
              "COLUMN_NAME": "source_suggestion_id",
              "REFERENCED_TABLE_NAME": "case_ai_suggestions",
              "REFERENCED_COLUMN_NAME": "suggestion_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "SET NULL"
            }
          ]
        },
        "checks": {
          "chk_case_task_source": {
            "clause": "(sourcein(_utf8mb4\\'STAFF_CREATED\\',_utf8mb4\\'AI_SUGGESTION_ACCEPTED\\',_utf8mb4\\'SYSTEM_REQUIRED\\'))",
            "enforced": "YES"
          },
          "chk_case_task_type": {
            "clause": "(task_typein(_utf8mb4\\'CUSTOMER_CONTACT\\',_utf8mb4\\'INSTITUTION_VERIFICATION\\',_utf8mb4\\'TRANSACTION_REVIEW\\',_utf8mb4\\'PROTECTIVE_ACTION\\',_utf8mb4\\'DOCUMENT_REVIEW\\',_utf8mb4\\'OTHER\\'))",
            "enforced": "YES"
          },
          "chk_case_task_priority": {
            "clause": "(priorityin(_utf8mb4\\'URGENT\\',_utf8mb4\\'HIGH\\',_utf8mb4\\'NORMAL\\'))",
            "enforced": "YES"
          },
          "chk_case_task_status": {
            "clause": "(statusin(_utf8mb4\\'TODO\\',_utf8mb4\\'IN_PROGRESS\\',_utf8mb4\\'BLOCKED\\',_utf8mb4\\'COMPLETED\\',_utf8mb4\\'CANCELLED\\'))",
            "enforced": "YES"
          },
          "chk_case_task_visibility": {
            "clause": "(customer_visibilityin(_utf8mb4\\'INTERNAL_ONLY\\',_utf8mb4\\'RESULT_SHAREABLE\\',_utf8mb4\\'RESULT_PUBLISHED\\'))",
            "enforced": "YES"
          },
          "chk_case_task_completed": {
            "clause": "((status<>_utf8mb4\\'COMPLETED\\')or((result_summaryisnotnull)and(completed_byisnotnull)and(completed_atisnotnull)))",
            "enforced": "YES"
          },
          "chk_case_task_cancelled": {
            "clause": "((status<>_utf8mb4\\'CANCELLED\\')or(cancellation_reasonisnotnull))",
            "enforced": "YES"
          }
        }
      },
      "case_transactions": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "id": {
            "COLUMN_TYPE": "bigint unsigned",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "auto_increment",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "transaction_type": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "transaction_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "amount": {
            "COLUMN_TYPE": "decimal(19,2)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "account_number": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "counterparty_name": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "counterparty_account": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "bank_name": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "memo": {
            "COLUMN_TYPE": "varchar(500)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "source": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "MANUAL",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_case_transactions_case_at": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "transaction_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_case_transactions_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ]
        },
        "checks": {}
      },
      "cases": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_name": {
            "COLUMN_TYPE": "varchar(200)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "client_request_id": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "risk_level": {
            "COLUMN_TYPE": "enum('NORMAL','LOW','HIGH')",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "risk_score": {
            "COLUMN_TYPE": "decimal(9,6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "mode": {
            "COLUMN_TYPE": "enum('PREVENT','RECOVERY','CLOSED')",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "PREVENT",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status": {
            "COLUMN_TYPE": "enum('NEW','TRIAGE','VERIFYING','IN_PROGRESS','CLOSED')",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "TRIAGE",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "version": {
            "COLUMN_TYPE": "int",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "context_revision": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "initial_brief": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "diagnosis_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "victim_transfer_status": {
            "COLUMN_TYPE": "varchar(30)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "actual_loss_amount_krw": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "deleted_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "client_request_id": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "client_request_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {},
        "checks": {}
      },
      "context_features": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "feature_id": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "auto_increment",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "segment_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "feature_key": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "feature_value": {
            "COLUMN_TYPE": "decimal(18,6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "source": {
            "COLUMN_TYPE": "varchar(50)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "fk_features_segment": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "segment_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "idx_context_features_case_key": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "feature_key",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "feature_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_features_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ],
          "fk_features_segment": [
            {
              "COLUMN_NAME": "segment_id",
              "REFERENCED_TABLE_NAME": "analysis_segments",
              "REFERENCED_COLUMN_NAME": "segment_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "customer_questions": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "question_id": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "source": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "target_field": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "question_text": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "reason": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "priority": {
            "COLUMN_TYPE": "varchar(2)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "PENDING",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "sequence": {
            "COLUMN_TYPE": "int",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "requested_by": {
            "COLUMN_TYPE": "varchar(80)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "asked_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "answered_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "options_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "allow_multi_select": {
            "COLUMN_TYPE": "tinyint(1)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "0",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "question_message_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "answer_message_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "answer_text": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "question_version": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "answer_payload_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "answer_question_version": {
            "COLUMN_TYPE": "bigint",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_customer_questions_case": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "sequence",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "question_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_customer_questions_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "message_context_extractions": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "extraction_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "message_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status": {
            "COLUMN_TYPE": "varchar(16)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "PENDING",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "attempts": {
            "COLUMN_TYPE": "int",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "0",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "last_error": {
            "COLUMN_TYPE": "varchar(1000)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "model_version": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "prompt_version": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "completed_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_message_context_extraction_case": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "created_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "idx_message_context_extraction_retry": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "status",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "attempts",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "updated_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "extraction_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_message_context_extraction_message": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "message_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_message_context_extraction_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ],
          "fk_message_context_extraction_message": [
            {
              "COLUMN_NAME": "message_id",
              "REFERENCED_TABLE_NAME": "messages",
              "REFERENCED_COLUMN_NAME": "message_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "CASCADE"
            }
          ]
        },
        "checks": {
          "chk_message_context_extraction_status": {
            "clause": "(statusin(_utf8mb4\\'PENDING\\',_utf8mb4\\'PROCESSING\\',_utf8mb4\\'COMPLETED\\',_utf8mb4\\'FAILED\\',_utf8mb4\\'SKIPPED\\'))",
            "enforced": "YES"
          },
          "chk_message_context_extraction_attempts": {
            "clause": "(attemptsbetween0and3)",
            "enforced": "YES"
          }
        }
      },
      "messages": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "message_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "actor_type": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "content": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "channel": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CUSTOMER",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "audience": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CUSTOMER",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "mentions_json": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "reply_to_message_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "client_request_id": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "actor_user_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "actor_display_name": {
            "COLUMN_TYPE": "varchar(80)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "actor_role": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "visibility": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CUSTOMER",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "message_kind": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CHAT",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "private_owner_user_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "attachments_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_messages_case_cursor": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "created_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "message_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "message_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "uq_messages_case_client_request": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "client_request_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_messages_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "personal_notes": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "note_id": {
            "COLUMN_TYPE": "varchar(100)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "author_id": {
            "COLUMN_TYPE": "varchar(80)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "content": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "visibility": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "PRIVATE_TO_AUTHOR",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_personal_notes_author": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "author_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "updated_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "note_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_personal_notes_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "schema_migrations": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "migration_name": {
            "COLUMN_TYPE": "varchar(255)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "applied_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "CURRENT_TIMESTAMP(6)",
            "EXTRA": "DEFAULT_GENERATED",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "migration_name",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {},
        "checks": {}
      },
      "verification_tasks": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "verification_task_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "claim": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "target": {
            "COLUMN_TYPE": "varchar(255)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "PENDING",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "version": {
            "COLUMN_TYPE": "int",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "1",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "updated_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "result_summary": {
            "COLUMN_TYPE": "text",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "evidence_url": {
            "COLUMN_TYPE": "varchar(2000)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "verified_by": {
            "COLUMN_TYPE": "varchar(80)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "rag_source": {
            "COLUMN_TYPE": "varchar(255)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "customer_visible": {
            "COLUMN_TYPE": "tinyint(1)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "0",
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_verification_tasks_case": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "created_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "verification_task_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_verification_tasks_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      },
      "voice_sessions": {
        "engine": "InnoDB",
        "collation": "utf8mb4_unicode_ci",
        "columns": {
          "session_id": {
            "COLUMN_TYPE": "varchar(64)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "case_id": {
            "COLUMN_TYPE": "varchar(32)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "status": {
            "COLUMN_TYPE": "enum('REQUESTED','ACTIVE','ENDED','FAILED')",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": "REQUESTED",
            "EXTRA": "",
            "CHARACTER_SET_NAME": "utf8mb4",
            "COLLATION_NAME": "utf8mb4_unicode_ci",
            "GENERATION_EXPRESSION": ""
          },
          "participants_json": {
            "COLUMN_TYPE": "json",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "started_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "ended_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "YES",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          },
          "created_at": {
            "COLUMN_TYPE": "datetime(6)",
            "IS_NULLABLE": "NO",
            "COLUMN_DEFAULT": null,
            "EXTRA": "",
            "CHARACTER_SET_NAME": null,
            "COLLATION_NAME": null,
            "GENERATION_EXPRESSION": ""
          }
        },
        "indexes": {
          "idx_voice_sessions_case": [
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "case_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            },
            {
              "NON_UNIQUE": 1,
              "COLUMN_NAME": "created_at",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ],
          "PRIMARY": [
            {
              "NON_UNIQUE": 0,
              "COLUMN_NAME": "session_id",
              "SUB_PART": null,
              "INDEX_TYPE": "BTREE",
              "COLLATION": "A",
              "IS_VISIBLE": "YES"
            }
          ]
        },
        "foreign_keys": {
          "fk_voice_sessions_case": [
            {
              "COLUMN_NAME": "case_id",
              "REFERENCED_TABLE_NAME": "cases",
              "REFERENCED_COLUMN_NAME": "case_id",
              "UPDATE_RULE": "NO ACTION",
              "DELETE_RULE": "NO ACTION"
            }
          ]
        },
        "checks": {}
      }
    },
    "triggers": {
      "trg_messages_context_revision_insert": {
        "EVENT_MANIPULATION": "INSERT",
        "EVENT_OBJECT_TABLE": "messages",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_messages_context_revision_delete": {
        "EVENT_MANIPULATION": "DELETE",
        "EVENT_OBJECT_TABLE": "messages",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=old.case_id"
      },
      "trg_verifications_context_revision_insert": {
        "EVENT_MANIPULATION": "INSERT",
        "EVENT_OBJECT_TABLE": "verification_tasks",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_verifications_context_revision_update": {
        "EVENT_MANIPULATION": "UPDATE",
        "EVENT_OBJECT_TABLE": "verification_tasks",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+if(not(old.claim<=>new.claim)ornot(old.target<=>new.target)ornot(old.status<=>new.status)ornot(old.result_summary<=>new.result_summary),1,0)wherecase_id=new.case_id"
      },
      "trg_verifications_context_revision_delete": {
        "EVENT_MANIPULATION": "DELETE",
        "EVENT_OBJECT_TABLE": "verification_tasks",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=old.case_id"
      },
      "trg_context_facts_v2_insert": {
        "EVENT_MANIPULATION": "INSERT",
        "EVENT_OBJECT_TABLE": "case_context_facts_v2",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_context_facts_v2_update": {
        "EVENT_MANIPULATION": "UPDATE",
        "EVENT_OBJECT_TABLE": "case_context_facts_v2",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_context_facts_v2_delete": {
        "EVENT_MANIPULATION": "DELETE",
        "EVENT_OBJECT_TABLE": "case_context_facts_v2",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=old.case_id"
      },
      "trg_case_gaps_insert": {
        "EVENT_MANIPULATION": "INSERT",
        "EVENT_OBJECT_TABLE": "case_gaps",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_case_gaps_update": {
        "EVENT_MANIPULATION": "UPDATE",
        "EVENT_OBJECT_TABLE": "case_gaps",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_case_gaps_delete": {
        "EVENT_MANIPULATION": "DELETE",
        "EVENT_OBJECT_TABLE": "case_gaps",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=old.case_id"
      },
      "trg_ai_suggestions_insert": {
        "EVENT_MANIPULATION": "INSERT",
        "EVENT_OBJECT_TABLE": "case_ai_suggestions",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_ai_suggestions_update": {
        "EVENT_MANIPULATION": "UPDATE",
        "EVENT_OBJECT_TABLE": "case_ai_suggestions",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_ai_suggestions_delete": {
        "EVENT_MANIPULATION": "DELETE",
        "EVENT_OBJECT_TABLE": "case_ai_suggestions",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=old.case_id"
      },
      "trg_case_tasks_insert": {
        "EVENT_MANIPULATION": "INSERT",
        "EVENT_OBJECT_TABLE": "case_tasks",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_case_tasks_update": {
        "EVENT_MANIPULATION": "UPDATE",
        "EVENT_OBJECT_TABLE": "case_tasks",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_case_tasks_delete": {
        "EVENT_MANIPULATION": "DELETE",
        "EVENT_OBJECT_TABLE": "case_tasks",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=old.case_id"
      },
      "trg_case_decisions_insert": {
        "EVENT_MANIPULATION": "INSERT",
        "EVENT_OBJECT_TABLE": "case_decisions",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_case_decisions_delete": {
        "EVENT_MANIPULATION": "DELETE",
        "EVENT_OBJECT_TABLE": "case_decisions",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=old.case_id"
      },
      "trg_questions_context_revision_insert": {
        "EVENT_MANIPULATION": "INSERT",
        "EVENT_OBJECT_TABLE": "customer_questions",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_questions_context_revision_delete": {
        "EVENT_MANIPULATION": "DELETE",
        "EVENT_OBJECT_TABLE": "customer_questions",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=old.case_id"
      },
      "trg_questions_context_revision_update": {
        "EVENT_MANIPULATION": "UPDATE",
        "EVENT_OBJECT_TABLE": "customer_questions",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+if(not(old.target_field<=>new.target_field)ornot(old.question_text<=>new.question_text)ornot(old.reason<=>new.reason)ornot(old.priority<=>new.priority)ornot(old.status<=>new.status)ornot(old.answer_text<=>new.answer_text)ornot(old.answer_payload_json<=>new.answer_payload_json),1,0)wherecase_id=new.case_id"
      },
      "trg_cases_context_revision_update": {
        "EVENT_MANIPULATION": "UPDATE",
        "EVENT_OBJECT_TABLE": "cases",
        "ACTION_TIMING": "BEFORE",
        "ACTION_STATEMENT": "setnew.context_revision=greatest(new.context_revision,old.context_revision+if(not(old.mode<=>new.mode)ornot(old.status<=>new.status)ornot(old.diagnosis_json<=>new.diagnosis_json)ornot(old.victim_transfer_status<=>new.victim_transfer_status)ornot(old.actual_loss_amount_krw<=>new.actual_loss_amount_krw),1,0))"
      },
      "trg_actions_context_revision_insert": {
        "EVENT_MANIPULATION": "INSERT",
        "EVENT_OBJECT_TABLE": "actions",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=new.case_id"
      },
      "trg_actions_context_revision_update": {
        "EVENT_MANIPULATION": "UPDATE",
        "EVENT_OBJECT_TABLE": "actions",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+if(not(old.action_type<=>new.action_type)ornot(old.status<=>new.status)ornot(old.note<=>new.note),1,0)wherecase_id=new.case_id"
      },
      "trg_actions_context_revision_delete": {
        "EVENT_MANIPULATION": "DELETE",
        "EVENT_OBJECT_TABLE": "actions",
        "ACTION_TIMING": "AFTER",
        "ACTION_STATEMENT": "updatecasessetcontext_revision=context_revision+1wherecase_id=old.case_id"
      }
    }
  },
  "counts": {
    "actions": 76,
    "analysis_segments": 94,
    "bank_staff_directory": 12,
    "case_ai_suggestions": 0,
    "case_context_facts_v2": 264,
    "case_context_item_history": 0,
    "case_context_items": 0,
    "case_context_observations": 0,
    "case_context_projections": 17,
    "case_context_signals": 0,
    "case_context_v2_history": 258,
    "case_decisions": 0,
    "case_events": 351,
    "case_gaps": 0,
    "case_inputs": 17,
    "case_members": 26,
    "case_presence": 21,
    "case_report_sections": 119,
    "case_reports": 17,
    "case_semantic_atoms": 129,
    "case_semantic_relations": 16,
    "case_tasks": 0,
    "case_transactions": 0,
    "cases": 17,
    "context_features": 2584,
    "customer_questions": 20,
    "message_context_extractions": 139,
    "messages": 199,
    "personal_notes": 0,
    "schema_migrations": 30,
    "verification_tasks": 0,
    "voice_sessions": 0
  },
  "integrity": {
    "foreign_keys_checked": 35,
    "foreign_key_violations": [],
    "case_orphans": []
  },
  "applied": [
    "001_core_case_diagnosis.sql",
    "002_initial_live_report.sql",
    "003_expand_risk_score_precision.sql",
    "004_case_messages_and_event_actor.sql",
    "005_verification_actions.sql",
    "006_case_version.sql",
    "007_voice_sessions.sql",
    "008_collaboration_channels.sql",
    "009_case_attachments.sql",
    "009_mysql_parity_workflow.sql",
    "010_case_fact_question_link.sql",
    "011_message_idempotency.sql",
    "012_context_items.sql",
    "013_context_projection_revision.sql",
    "014_case_context_v2_foundation.sql",
    "015_context_panel_v3.sql",
    "016_case_name.sql",
    "017_structured_context_resources.sql",
    "018_action_contract_fields.sql",
    "019_context_observations.sql",
    "020_bank_staff_directory.sql",
    "021_bank_staff_assignment_fields.sql",
    "021_create_case_transactions.sql",
    "022_case_member_assignment_roles.sql",
    "023_bank_staff_demo_seed.sql",
    "024_bank_staff_role_schema_alignment.sql",
    "025_retire_transcript_storage.sql",
    "026_retire_attachments.sql",
    "027_migrate_legacy_case_facts_to_v2.sql",
    "028_retire_legacy_case_facts.sql"
  ],
  "pending": [],
  "historical_records": [
    "021_bank_staff_assignment_fields.sql"
  ]
}
