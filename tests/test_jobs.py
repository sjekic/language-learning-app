"""
Unit tests for jobs module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
import json

# Mock Azure imports before importing jobs modules
sys.modules['azure'] = MagicMock()
sys.modules['azure.storage'] = MagicMock()
sys.modules['azure.storage.blob'] = MagicMock()
sys.modules['azure.storage.blob'].BlobServiceClient = MagicMock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'jobs', 'src'))

from common import utils
from common import storage
import chunk_jobs
import final_assembly_job
import manifest
import orchestrator

# Note: Pollers are scripts, so we test them by importing their main function if possible,
# or by mocking the script execution. Here we will try to direct-import check.
# Checked files: they have "if __name__ == '__main__': main()", so safe to import.
import chunk_poller
import manifest_poller
import orchestrator_poller
import final_assembly_poller


class TestUtils:
    """Tests for common/utils.py"""
    
    def test_read_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        assert utils.read_file(str(test_file)) == "test content"
    
    def test_read_file_nonexistent(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            utils.read_file(str(tmp_path / "nonexistent.txt"))
    
    def test_write_json(self, tmp_path):
        test_file = tmp_path / "test.json"
        test_data = {"key": "value"}
        utils.write_json(str(test_file), test_data)
        assert json.loads(test_file.read_text()) == test_data
    
    def test_write_text(self, tmp_path):
        test_file = tmp_path / "test.txt"
        utils.write_text(str(test_file), "test content")
        assert test_file.read_text() == "test content"


class TestStorage:
    """Tests for common/storage.py"""
    
    def test_upload_text(self):
        mock_blob_client = Mock()
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_blob_client.return_value = mock_blob_client
            storage.upload_text("container", "blob", "content")
            mock_blob_client.upload_blob.assert_called_once()
    
    def test_download_text(self):
        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value.readall.return_value.decode.return_value = "content"
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_blob_client.return_value = mock_blob_client
            assert storage.download_text("container", "blob") == "content"


class TestChunkJobs:
    """Tests for chunk_jobs.py"""
    
    def test_get_cefr_guidelines(self):
        # The guidelines return strings, just check for non-empty result
        # and different results for different levels if applicable
        g1 = chunk_jobs.get_cefr_guidelines("A1")
        assert isinstance(g1, str)
        assert len(g1) > 0

    def test_get_params_from_trigger(self):
        # Test get_params_from_trigger independently
        mock_blob = Mock()
        mock_blob.name = "trigger"
        mock_blob_client = Mock()
        # Mock legacy trigger format for simplicity, or full format
        mock_blob_client.download_blob.return_value.readall.return_value.decode.return_value = json.dumps({"story_id": "s1", "chunk_id": 1}).encode()
        
        with patch('chunk_jobs.BlobServiceClient') as mock_service:
            mock_service.from_connection_string.return_value.get_container_client.return_value.list_blobs.return_value = [mock_blob]
            mock_service.from_connection_string.return_value.get_blob_client.return_value = mock_blob_client
            with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "conn"}):
                s_id, b_id, c_start, c_end = chunk_jobs.get_params_from_trigger()
                assert s_id == "s1"
                assert b_id == 1
                assert c_start == 1
                assert c_end == 1

    def test_main(self):
        with patch('chunk_jobs.get_params_from_trigger', return_value=("story_id", 1, 1, 1)):
            with patch('chunk_jobs.download_text', side_effect=[
                json.dumps({"storyId": "s1", "readingLevel": "A1", "genre": "g", "language": "l", "title": "Test Title", "chapters": [{"title": "c1", "summary": "s1"}]}), # manifest
                json.dumps({"characters": []}) # story_bible
            ]):
                with patch('chunk_jobs.upload_json') as mock_upload:
                    with patch('chunk_jobs.OpenAI') as mock_openai:
                        mock_openai.return_value.chat.completions.create.return_value.choices = [Mock(message=Mock(content="Generated"))]
                        chunk_jobs.main()
                        assert mock_upload.called

class TestFinalAssemblyJob:
    """Tests for final_assembly_job.py"""
    
    def test_main(self):
        with patch('final_assembly_job.get_story_id_from_trigger', return_value="s1"):
            with patch('final_assembly_job.download_text', side_effect=[
                json.dumps({"storyId": "s1", "chapters": [{"chunkId": 1}]}), # manifest
                json.dumps({"title": "t", "coverUrl": "u"}), # cover
                json.dumps({"chunkId": 1, "content": "c"}) # chunk
            ]):
                with patch('final_assembly_job.upload_json') as mock_upload:
                    final_assembly_job.main()
                    mock_upload.assert_called_once()


class TestManifest:
    """Tests for manifest.py"""
    
    def test_main(self):
        with patch('manifest.get_story_id_from_trigger', return_value="s1"):
            with patch('manifest.download_text', return_value=json.dumps({"userPrompt": "p", "language": "l", "genre": "g", "readingLevel": "l"})):
                with patch('manifest.upload_json') as mock_upload:
                    with patch('manifest.BlobServiceClient') as mock_blob:
                        with patch('manifest.OpenAI') as mock_openai:
                            mock_openai.return_value.chat.completions.create.return_value.choices = [Mock(message=Mock(content=json.dumps({"title": "t", "chapters": []})))]
                            manifest.main()
                            assert mock_upload.called


class TestOrchestrator:
    """Tests for orchestrator.py"""
    
    def test_get_params_from_trigger(self):
        mock_blob = Mock()
        mock_blob.name = "trigger"
        # Mock payload: expected_chunks=10
        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value.readall.return_value.decode.return_value = json.dumps({"story_id": "s1", "expected_chunks": 5})
        
        with patch('orchestrator.BlobServiceClient') as mock_service:
            mock_service.from_connection_string.return_value.get_container_client.return_value.list_blobs.return_value = [mock_blob]
            mock_service.from_connection_string.return_value.get_blob_client.return_value = mock_blob_client
            
            with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "conn"}):
                story_id, chunks = orchestrator.get_params_from_trigger()
                assert story_id == "s1"
                assert chunks == 5
    
    def test_main_success(self):
        # Test full flow where chunks are ready
        with patch('orchestrator.get_params_from_trigger', return_value=("s1", 1)):
            with patch('orchestrator.list_blobs', return_value=["Users/s1/chunks/chunk_1.json"]):
                with patch('orchestrator.BlobServiceClient') as mock_service:
                    with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "conn"}):
                        orchestrator.main()
                        # Should have created final assembly trigger
                        mock_service.from_connection_string.return_value.get_blob_client.return_value.upload_blob.assert_called()

    def test_main_timeout(self):
        with patch('orchestrator.get_params_from_trigger', return_value=("s1", 1)):
            with patch('orchestrator.list_blobs', return_value=[]):
                with patch('time.sleep'): # Skip sleep
                    with patch('orchestrator.BlobServiceClient'):
                        orchestrator.main() 


class TestPollers:
    """Tests for poller scripts"""
    
    def test_chunk_poller(self):
        with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "conn", "JOB_COMPLETION_INDEX": "0"}):
            mock_blob = Mock()
            mock_blob.name = "trigger1"
            mock_blob_client = Mock()
            mock_blob_client.download_blob.return_value.readall.return_value = json.dumps({"story_id": "s1", "chunk_id": 1, "trigger_id": "t1"}).encode()
            
            with patch('chunk_poller.BlobServiceClient') as mock_service:
                mock_service.from_connection_string.return_value.get_container_client.return_value.list_blobs.return_value = [mock_blob]
                mock_service.from_connection_string.return_value.get_container_client.return_value.get_blob_client.return_value = mock_blob_client
                
                with patch('chunk_jobs.main') as mock_job_main:
                    with patch('sys.exit'): # Mock sys.exit to prevent abort
                        chunk_poller.main()
                        mock_job_main.assert_called_once()
    
    def test_chunk_poller_no_triggers(self):
        with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "conn"}):
            with patch('chunk_poller.BlobServiceClient') as mock_service:
                mock_service.from_connection_string.return_value.get_container_client.return_value.list_blobs.return_value = []
                with patch('sys.exit') as mock_exit:
                    chunk_poller.main()
                    mock_exit.assert_called_with(0)

    def test_manifest_poller(self):
        with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "conn"}):
            mock_blob = Mock()
            mock_blob.name = "trigger1"
            mock_blob_client = Mock()
            mock_blob_client.download_blob.return_value.readall.return_value = json.dumps({"story_id": "s1", "trigger_id": "t1"}).encode()
            
            with patch('manifest_poller.BlobServiceClient') as mock_service:
                mock_service.from_connection_string.return_value.get_container_client.return_value.list_blobs.return_value = [mock_blob]
                mock_service.from_connection_string.return_value.get_container_client.return_value.get_blob_client.return_value = mock_blob_client
                
                with patch('manifest.main') as mock_job_main:
                    with patch('sys.exit'):
                        manifest_poller.main() 
                        mock_job_main.assert_called_once()

    def test_manifest_poller_no_triggers(self):
        with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "conn"}):
            with patch('manifest_poller.BlobServiceClient') as mock_service:
                mock_service.from_connection_string.return_value.get_container_client.return_value.list_blobs.return_value = []
                with patch('sys.exit') as mock_exit:
                    manifest_poller.main()
                    mock_exit.assert_called_with(0)

    def test_final_assembly_poller(self):
        with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "conn"}):
            mock_blob = Mock()
            mock_blob.name = "trigger1"
            mock_blob_client = Mock()
            mock_blob_client.download_blob.return_value.readall.return_value = json.dumps({"story_id": "s1", "trigger_id": "t1"}).encode()
            
            with patch('final_assembly_poller.BlobServiceClient') as mock_service:
                mock_service.from_connection_string.return_value.get_container_client.return_value.list_blobs.return_value = [mock_blob]
                mock_service.from_connection_string.return_value.get_container_client.return_value.get_blob_client.return_value = mock_blob_client
                with patch('final_assembly_job.main'):
                    with patch('sys.exit'):
                         final_assembly_poller.main()

    def test_orchestrator_poller(self):
        with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "conn"}):
            mock_blob = Mock()
            mock_blob.name = "trigger1"
            mock_blob_client = Mock()
            mock_blob_client.download_blob.return_value.readall.return_value = json.dumps({"story_id": "s1", "trigger_id": "t1"}).encode()
            
            with patch('orchestrator_poller.BlobServiceClient') as mock_service:
                mock_service.from_connection_string.return_value.get_container_client.return_value.list_blobs.return_value = [mock_blob]
                mock_service.from_connection_string.return_value.get_container_client.return_value.get_blob_client.return_value = mock_blob_client
                with patch('orchestrator.main'):
                    with patch('sys.exit'):
                         orchestrator_poller.main()
