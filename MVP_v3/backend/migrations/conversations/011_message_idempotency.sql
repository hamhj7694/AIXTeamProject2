ALTER TABLE messages
    ADD UNIQUE KEY uq_messages_case_client_request (case_id, client_request_id);
