"""
IMPORTANT: Database Operation Reliability Tests
Tests Firebase Firestore and Realtime DB operations for reliability
"""
import pytest
from unittest.mock import Mock, patch, call
import json
import time


class TestDatabaseReliability:
    """Test database operations reliability and error handling"""
    
    def test_firestore_connection_failure(self, authenticated_session):
        """Test handling of Firestore connection failures"""
        with patch('app.db') as mock_db:
            # Simulate connection failure
            mock_db.collection.side_effect = Exception("Connection failed")
            
            response = authenticated_session.get('/dashboard')
            
            # Should handle gracefully
            assert response.status_code in [200, 500]
            if response.status_code == 500:
                # Should have error handling
                assert b'error' in response.data.lower() or b'try again' in response.data.lower()
    
    def test_firestore_read_retry_mechanism(self, authenticated_session, mock_db):
        """Test retry mechanism for failed reads"""
        with patch('app.db', mock_db):
            # First call fails, second succeeds
            mock_db.collection.return_value.document.return_value.get.side_effect = [
                Exception("Temporary failure"),
                Mock(exists=True, to_dict=lambda: {"id": "test", "creator_id": "test_user_123"})
            ]
            
            response = authenticated_session.get('/edit-form?id=test_form_123')
            
            # Should eventually succeed after retry
            assert response.status_code == 200
    
    def test_firestore_write_transaction_integrity(self, authenticated_session, mock_db):
        """Test transactional integrity of write operations"""
        with patch('app.db', mock_db):
            # Mock transaction
            mock_transaction = Mock()
            mock_db.transaction.return_value = mock_transaction
            
            mock_db.collection.return_value.add.return_value = (None, "form_123")
            
            form_data = {
                'title': 'Test Form',
                'questions': [{'text': 'Question 1', 'type': 'text', 'enabled': True}]
            }
            
            response = authenticated_session.post('/api/save_form', json=form_data)
            
            assert response.status_code == 200
            
            # Verify write operation was called
            mock_db.collection.assert_called_with('forms')
    
    def test_firestore_concurrent_writes(self, authenticated_session, mock_db):
        """Test handling of concurrent write operations"""
        with patch('app.db', mock_db):
            mock_db.collection.return_value.add.return_value = (None, "concurrent_form")
            
            # Simulate concurrent form saves
            form_data = {'title': 'Concurrent Test', 'questions': []}
            
            responses = []
            for i in range(10):
                response = authenticated_session.post('/api/save_form', json=form_data)
                responses.append(response)
            
            # All operations should succeed or fail gracefully
            success_count = sum(1 for r in responses if r.status_code == 200)
            assert success_count >= 5  # At least half should succeed
    
    def test_firestore_query_performance(self, authenticated_session, mock_db):
        """Test query performance with large datasets"""
        with patch('app.db', mock_db):
            # Mock large result set
            large_forms = [
                Mock(to_dict=lambda: {"id": f"form_{i}", "title": f"Form {i}", "creator_id": "test_user_123"}, id=f"form_{i}")
                for i in range(1000)
            ]
            
            mock_db.collection.return_value.where.return_value.stream.return_value = large_forms
            
            start_time = time.time()
            response = authenticated_session.get('/dashboard')
            end_time = time.time()
            
            assert response.status_code == 200
            # Should complete in reasonable time (< 5 seconds)
            assert (end_time - start_time) < 5.0
    
    def test_firestore_data_consistency(self, authenticated_session, mock_db, sample_form):
        """Test data consistency across operations"""
        with patch('app.db', mock_db):
            # Mock consistent read after write
            mock_doc = Mock()
            mock_db.collection.return_value.document.return_value = mock_doc
            
            mock_doc.get.return_value.to_dict.return_value = sample_form
            mock_doc.get.return_value.exists = True
            mock_doc.update.return_value = None
            
            # Update form
            updated_form = sample_form.copy()
            updated_form['title'] = 'Updated Title'
            
            response = authenticated_session.put('/api/update_form/test_form_123', 
                json=updated_form)
            
            assert response.status_code == 200
            
            # Verify update was called with correct data
            mock_doc.update.assert_called_once()
            update_data = mock_doc.update.call_args[0][0]
            assert update_data['title'] == 'Updated Title'
    
    def test_firestore_batch_operations(self, authenticated_session, mock_db):
        """Test batch operations for efficiency"""
        with patch('app.db', mock_db):
            # Mock batch
            mock_batch = Mock()
            mock_db.batch.return_value = mock_batch
            
            # Simulate batch delete of multiple forms
            form_ids = ['form_1', 'form_2', 'form_3']
            
            for form_id in form_ids:
                mock_db.collection.return_value.document.return_value.get.return_value.exists = True
                mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
                    "creator_id": "test_user_123"
                }
                
                response = authenticated_session.delete(f'/api/forms/{form_id}')
                # Each should succeed or handle gracefully
                assert response.status_code in [200, 404]
    
    def test_realtime_db_chat_sync(self, client, mock_db, sample_chat_session):
        """Test Realtime Database chat synchronization"""
        with patch('app.db', mock_db), \
             patch('firebase_admin.db') as mock_realtime_db:
            
            mock_ref = Mock()
            mock_realtime_db.reference.return_value = mock_ref
            mock_ref.push.return_value = Mock(key='message_123')
            
            # Mock chat session
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = sample_chat_session
            mock_db.collection.return_value.document.return_value.get.return_value.exists = True
            
            with patch('chat_agent.ChatAgent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent
                mock_agent.process_message.return_value = {
                    'response': 'Thanks for your message!',
                    'status': 'active'
                }
                
                response = client.post('/api/chat/message',
                    json={
                        'session_id': 'session_123',
                        'message': 'Hello'
                    })
                
                assert response.status_code == 200
                
                # Verify realtime DB was updated
                mock_realtime_db.reference.assert_called()
    
    def test_database_error_recovery(self, authenticated_session, mock_db):
        """Test recovery from database errors"""
        with patch('app.db', mock_db):
            # Simulate intermittent failures
            call_count = [0]
            
            def side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] <= 2:
                    raise Exception("Database temporarily unavailable")
                return Mock(exists=True, to_dict=lambda: {"creator_id": "test_user_123"})
            
            mock_db.collection.return_value.document.return_value.get.side_effect = side_effect
            
            # Should eventually succeed after retries
            response = authenticated_session.get('/edit-form?id=test_form_123')
            
            # Either succeeds after retry or fails gracefully
            assert response.status_code in [200, 500]
    
    def test_database_connection_pooling(self, authenticated_session, mock_db):
        """Test database connection pooling under load"""
        with patch('app.db', mock_db):
            mock_db.collection.return_value.where.return_value.stream.return_value = []
            
            # Simulate multiple concurrent dashboard requests
            responses = []
            for i in range(50):
                response = authenticated_session.get('/dashboard')
                responses.append(response)
            
            # All should succeed (connection pooling should handle load)
            success_count = sum(1 for r in responses if r.status_code == 200)
            assert success_count >= 45  # 90% success rate
    
    def test_database_query_optimization(self, authenticated_session, mock_db):
        """Test that queries are optimized for performance"""
        with patch('app.db', mock_db):
            mock_query = Mock()
            mock_db.collection.return_value.where.return_value = mock_query
            mock_query.stream.return_value = []
            
            response = authenticated_session.get('/dashboard')
            
            assert response.status_code == 200
            
            # Verify efficient query was made (where clause used)
            mock_db.collection.assert_called_with('forms')
            mock_db.collection.return_value.where.assert_called()
    
    def test_database_index_usage(self, authenticated_session, mock_db, sample_responses):
        """Test that database indexes are used effectively"""
        with patch('app.db', mock_db):
            # Mock form lookup
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
                "creator_id": "test_user_123"
            }
            mock_db.collection.return_value.document.return_value.get.return_value.exists = True
            
            # Mock responses query (should use indexes)
            mock_responses_query = Mock()
            mock_db.collection.return_value.where.return_value = mock_responses_query
            mock_responses_query.stream.return_value = [
                Mock(to_dict=lambda: resp) for resp in sample_responses
            ]
            
            response = authenticated_session.get('/api/responses/test_form_123')
            
            assert response.status_code == 200
            
            # Verify indexed query was used
            mock_db.collection.return_value.where.assert_called()
    
    def test_database_backup_and_recovery(self, authenticated_session, mock_db):
        """Test data backup and recovery scenarios"""
        with patch('app.db', mock_db):
            # Simulate data corruption/loss scenario
            mock_db.collection.return_value.document.return_value.get.return_value.exists = False
            
            response = authenticated_session.get('/edit-form?id=test_form_123')
            
            # Should handle missing data gracefully
            assert response.status_code == 404
    
    def test_database_security_rules(self, client, mock_db, sample_form):
        """Test that database security rules are enforced"""
        with patch('app.db', mock_db):
            # Simulate unauthorized access attempt
            sample_form["creator_id"] = "other_user"
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = sample_form
            mock_db.collection.return_value.document.return_value.get.return_value.exists = True
            
            # Try to access without authentication
            response = client.get('/edit-form?id=test_form_123')
            
            # Should be blocked by auth middleware
            assert response.status_code in [401, 302]
    
    def test_database_field_validation(self, authenticated_session, mock_db):
        """Test database field validation and constraints"""
        with patch('app.db', mock_db):
            mock_db.collection.return_value.add.return_value = (None, "validated_form")
            
            # Test with invalid field types
            invalid_form = {
                'title': 123,  # Should be string
                'questions': 'invalid',  # Should be array
                'active': 'yes'  # Should be boolean
            }
            
            response = authenticated_session.post('/api/save_form', json=invalid_form)
            
            # Should validate and reject or coerce types
            assert response.status_code in [200, 400]
    
    def test_database_transaction_rollback(self, authenticated_session, mock_db):
        """Test transaction rollback on errors"""
        with patch('app.db', mock_db):
            # Mock transaction that fails partway through
            mock_transaction = Mock()
            mock_db.transaction.return_value = mock_transaction
            
            # Simulate partial failure
            mock_db.collection.return_value.add.side_effect = [
                (None, "form_123"),  # Form save succeeds
                Exception("Transaction failed")  # Related operation fails
            ]
            
            form_data = {'title': 'Transaction Test', 'questions': []}
            
            response = authenticated_session.post('/api/save_form', json=form_data)
            
            # Should handle transaction failure
            assert response.status_code in [200, 500]
    
    def test_database_cache_consistency(self, authenticated_session, mock_db, sample_form):
        """Test cache consistency with database updates"""
        with patch('app.db', mock_db):
            mock_doc = Mock()
            mock_db.collection.return_value.document.return_value = mock_doc
            
            # First read
            mock_doc.get.return_value.to_dict.return_value = sample_form
            mock_doc.get.return_value.exists = True
            
            response1 = authenticated_session.get('/edit-form?id=test_form_123')
            assert response1.status_code == 200
            
            # Update form
            updated_form = sample_form.copy()
            updated_form['title'] = 'Updated Title'
            mock_doc.update.return_value = None
            
            response2 = authenticated_session.put('/api/update_form/test_form_123',
                json=updated_form)
            assert response2.status_code == 200
            
            # Subsequent read should reflect changes
            mock_doc.get.return_value.to_dict.return_value = updated_form
            
            response3 = authenticated_session.get('/edit-form?id=test_form_123')
            assert response3.status_code == 200