"""
Unit tests for jobs module
"""
import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
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
import cover_job
import final_assembly_job
import manifest


class TestUtils:
    """Tests for common/utils.py"""
    
    def test_parse_args_with_story_id(self):
        """Test parse args with story-id"""
        with patch('sys.argv', ['script.py', '--story-id', 'test-story-123']):
            args = utils.parse_args()
            assert args.story_id == 'test-story-123'
    
    def test_parse_args_with_chunk_id(self):
        """Test parse args with chunk-id"""
        with patch('sys.argv', ['script.py', '--story-id', 'test-story-123', '--chunk-id', '5']):
            args = utils.parse_args()
            assert args.story_id == 'test-story-123'
            assert args.chunk_id == 5
    
    def test_parse_args_from_env(self):
        """Test parse args from environment variable"""
        with patch.dict(os.environ, {'STORY_ID': 'env-story-123', 'CHUNK_ID': '10'}):
            with patch('sys.argv', ['script.py']):
                args = utils.parse_args()
                assert args.story_id == 'env-story-123'
                assert args.chunk_id == 10
    
    def test_parse_args_missing_story_id(self):
        """Test parse args without story-id"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('sys.argv', ['script.py']):
                with pytest.raises(ValueError, match="story-id is required"):
                    utils.parse_args()
    
    def test_parse_args_env_overrides_cli(self):
        """Test CLI args override environment variable"""
        with patch.dict(os.environ, {'STORY_ID': 'env-story-123'}):
            with patch('sys.argv', ['script.py', '--story-id', 'cli-story-123']):
                args = utils.parse_args()
                # CLI argument takes precedence
                assert args.story_id == 'cli-story-123'
    
    def test_parse_args_chunk_id_from_env_string(self):
        """Test parse args with chunk_id from env as string"""
        with patch.dict(os.environ, {'STORY_ID': 'env-story-123', 'CHUNK_ID': '10'}):
            with patch('sys.argv', ['script.py']):
                args = utils.parse_args()
                assert args.chunk_id == 10
    
    def test_read_file(self, tmp_path):
        """Test read file"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        result = utils.read_file(str(test_file))
        assert result == "test content"
    
    def test_read_file_nonexistent(self, tmp_path):
        """Test read file that doesn't exist"""
        with pytest.raises(FileNotFoundError):
            utils.read_file(str(tmp_path / "nonexistent.txt"))
    
    def test_write_json(self, tmp_path):
        """Test write JSON"""
        test_file = tmp_path / "test.json"
        test_data = {"key": "value", "number": 123}
        
        utils.write_json(str(test_file), test_data)
        
        assert test_file.exists()
        with open(test_file) as f:
            data = json.load(f)
            assert data == test_data
    
    def test_write_json_nested(self, tmp_path):
        """Test write JSON with nested data"""
        test_file = tmp_path / "test.json"
        test_data = {"key": "value", "nested": {"a": 1, "b": 2}}
        
        utils.write_json(str(test_file), test_data)
        
        assert test_file.exists()
        with open(test_file) as f:
            data = json.load(f)
            assert data == test_data
    
    def test_write_text(self, tmp_path):
        """Test write text"""
        test_file = tmp_path / "test.txt"
        
        utils.write_text(str(test_file), "test content")
        
        assert test_file.exists()
        assert test_file.read_text() == "test content"
    
    def test_write_text_multiline(self, tmp_path):
        """Test write text with multiline content"""
        test_file = tmp_path / "test.txt"
        content = "line 1\nline 2\nline 3"
        
        utils.write_text(str(test_file), content)
        
        assert test_file.exists()
        assert test_file.read_text() == content
    
    def test_write_json_creates_directory(self, tmp_path):
        """Test write JSON creates directory if needed"""
        test_file = tmp_path / "subdir" / "test.json"
        test_data = {"key": "value"}
        
        utils.write_json(str(test_file), test_data)
        
        assert test_file.exists()
        assert test_file.parent.exists()
    
    def test_write_text_creates_directory(self, tmp_path):
        """Test write text creates directory if needed"""
        test_file = tmp_path / "subdir" / "test.txt"
        
        utils.write_text(str(test_file), "test content")
        
        assert test_file.exists()
        assert test_file.parent.exists()


class TestStorage:
    """Tests for common/storage.py"""
    
    def test_upload_text(self):
        """Test upload text to blob"""
        mock_blob_client = Mock()
        mock_blob_client.upload_blob = Mock()
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_blob_client.return_value = mock_blob_client
            
            storage.upload_text("container", "path/to/blob.txt", "test content")
            mock_blob_client.upload_blob.assert_called_once()
    
    def test_download_text(self):
        """Test download text from blob"""
        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value.readall.return_value.decode.return_value = "test content"
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_blob_client.return_value = mock_blob_client
            
            result = storage.download_text("container", "path/to/blob.txt")
            assert result == "test content"
    
    def test_download_text_error(self):
        """Test download text with error"""
        mock_blob_client = Mock()
        mock_blob_client.download_blob.side_effect = Exception("Download failed")
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_blob_client.return_value = mock_blob_client
            
            with pytest.raises(Exception):
                storage.download_text("container", "path/to/blob.txt")
    
    def test_upload_json(self):
        """Test upload JSON to blob"""
        mock_blob_client = Mock()
        mock_blob_client.upload_blob = Mock()
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_blob_client.return_value = mock_blob_client
            
            test_data = {"key": "value"}
            storage.upload_json("container", "path/to/blob.json", test_data)
            mock_blob_client.upload_blob.assert_called_once()
    
    def test_upload_file(self, tmp_path):
        """Test upload file to blob"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        mock_blob_client = Mock()
        mock_blob_client.upload_blob = Mock()
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_blob_client.return_value = mock_blob_client
            
            storage.upload_file("container", "path/to/blob.txt", str(test_file))
            mock_blob_client.upload_blob.assert_called_once()
    
    def test_list_blobs(self):
        """Test list blobs"""
        mock_blob = Mock()
        mock_blob.name = "path/to/blob1.txt"
        mock_blob2 = Mock()
        mock_blob2.name = "path/to/blob2.txt"
        
        mock_container_client = Mock()
        mock_container_client.list_blobs.return_value = [mock_blob, mock_blob2]
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_container_client.return_value = mock_container_client
            
            result = storage.list_blobs("container", "path/to/")
            assert len(result) == 2
            assert "blob1.txt" in result[0]
            assert "blob2.txt" in result[1]
    
    def test_list_blobs_error(self):
        """Test list blobs with error"""
        mock_container_client = Mock()
        mock_container_client.list_blobs.side_effect = Exception("List failed")
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_container_client.return_value = mock_container_client
            
            with pytest.raises(Exception):
                storage.list_blobs("container", "path/to/")
    
    def test_upload_text_with_special_chars(self):
        """Test upload text with special characters"""
        mock_blob_client = Mock()
        mock_blob_client.upload_blob = Mock()
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_blob_client.return_value = mock_blob_client
            
            storage.upload_text("container", "path/to/blob.txt", "test content\nwith newlines\tand tabs")
            mock_blob_client.upload_blob.assert_called_once()
    
    def test_download_text_empty(self):
        """Test download text with empty content"""
        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value.readall.return_value.decode.return_value = ""
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_blob_client.return_value = mock_blob_client
            
            result = storage.download_text("container", "path/to/blob.txt")
            assert result == ""
    
    def test_upload_json_empty_dict(self):
        """Test upload JSON with empty dict"""
        mock_blob_client = Mock()
        mock_blob_client.upload_blob = Mock()
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_blob_client.return_value = mock_blob_client
            
            storage.upload_json("container", "path/to/blob.json", {})
            mock_blob_client.upload_blob.assert_called_once()
    
    def test_upload_json_with_none(self):
        """Test upload JSON with None values"""
        mock_blob_client = Mock()
        mock_blob_client.upload_blob = Mock()
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_blob_client.return_value = mock_blob_client
            
            test_data = {"key": "value", "none_value": None}
            storage.upload_json("container", "path/to/blob.json", test_data)
            mock_blob_client.upload_blob.assert_called_once()
    
    def test_list_blobs_empty(self):
        """Test list blobs with empty result"""
        mock_container_client = Mock()
        mock_container_client.list_blobs.return_value = []
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_container_client.return_value = mock_container_client
            
            result = storage.list_blobs("container", "path/to/")
            assert len(result) == 0
    
    def test_list_blobs_no_prefix(self):
        """Test list blobs without prefix"""
        mock_blob = Mock()
        mock_blob.name = "blob1.txt"
        mock_blob2 = Mock()
        mock_blob2.name = "blob2.txt"
        
        mock_container_client = Mock()
        mock_container_client.list_blobs.return_value = [mock_blob, mock_blob2]
        
        with patch('common.storage.blob') as mock_blob_service:
            mock_blob_service.get_container_client.return_value = mock_container_client
            
            result = storage.list_blobs("container", "")
            assert len(result) == 2


class TestChunkJobs:
    """Tests for chunk_jobs.py"""
    
    def test_main(self):
        """Test chunk_jobs main function"""
        mock_manifest = {"storyId": "test-story-123", "chunks": []}
        
        with patch('chunk_jobs.parse_args') as mock_args:
            mock_args.return_value.story_id = "test-story-123"
            mock_args.return_value.chunk_id = 1
            
            with patch('chunk_jobs.download_text', return_value=json.dumps(mock_manifest)):
                with patch('chunk_jobs.upload_json') as mock_upload:
                    chunk_jobs.main()
                    mock_upload.assert_called_once()


class TestCoverJob:
    """Tests for cover_job.py"""
    
    def test_main(self):
        """Test cover_job main function"""
        mock_manifest = {
            "storyId": "test-story-123",
            "userPrompt": "A test story"
        }
        
        with patch('cover_job.parse_args') as mock_args:
            mock_args.return_value.story_id = "test-story-123"
            
            with patch('cover_job.download_text', return_value=json.dumps(mock_manifest)):
                with patch('cover_job.upload_json') as mock_upload:
                    cover_job.main()
                    mock_upload.assert_called_once()


class TestFinalAssemblyJob:
    """Tests for final_assembly_job.py"""
    
    def test_main(self):
        """Test final_assembly_job main function"""
        mock_manifest = {
            "storyId": "test-story-123",
            "genre": "fantasy",
            "readingLevel": "A1"
        }
        
        mock_cover = {
            "storyId": "test-story-123",
            "title": "Test Story",
            "coverUrl": "https://test.com/cover.png"
        }
        
        mock_chunk1 = {"content": "Chunk 1 content"}
        mock_chunk2 = {"content": "Chunk 2 content"}
        
        with patch('final_assembly_job.parse_args') as mock_args:
            mock_args.return_value.story_id = "test-story-123"
            
            with patch('final_assembly_job.download_text') as mock_download:
                mock_download.side_effect = [
                    json.dumps(mock_manifest),
                    json.dumps(mock_cover),
                    json.dumps(mock_chunk1),
                    json.dumps(mock_chunk2),
                    Exception("No more chunks")
                ]
                
                with patch('final_assembly_job.upload_json') as mock_upload:
                    final_assembly_job.main()
                    mock_upload.assert_called_once()


class TestManifest:
    """Tests for manifest.py"""
    
    def test_main(self):
        """Test manifest main function"""
        mock_raw_data = {
            "userPrompt": "A test story",
            "genre": "fantasy",
            "readingLevel": "A1"
        }
        
        with patch('manifest.parse_args') as mock_args:
            mock_args.return_value.story_id = "test-story-123"
            
            with patch('manifest.download_text', return_value=json.dumps(mock_raw_data)):
                with patch('manifest.upload_json') as mock_upload:
                    manifest.main()
                    mock_upload.assert_called_once()
                    
                    # Check manifest structure
                    call_args = mock_upload.call_args
                    uploaded_data = call_args[0][2]  # Third argument is the data (dict)
                    assert uploaded_data["storyId"] == "test-story-123"
                    assert uploaded_data["userPrompt"] == "A test story"
                    assert uploaded_data["status"] == "pending"
    
    def test_main_missing_fields(self):
        """Test manifest main with missing fields"""
        mock_raw_data = {}
        
        with patch('manifest.parse_args') as mock_args:
            mock_args.return_value.story_id = "test-story-123"
            
            with patch('manifest.download_text', return_value=json.dumps(mock_raw_data)):
                with patch('manifest.upload_json') as mock_upload:
                    manifest.main()
                    mock_upload.assert_called_once()


class TestChunkJobsEdgeCases:
    """Additional tests for chunk_jobs.py"""
    
    def test_main_with_chunk_id(self):
        """Test chunk_jobs main function with chunk_id"""
        mock_manifest = {
            "storyId": "test-story-123",
            "chunks": []
        }
        
        with patch('chunk_jobs.parse_args') as mock_args:
            mock_args.return_value.story_id = "test-story-123"
            mock_args.return_value.chunk_id = 5
            
            with patch('chunk_jobs.download_text', return_value=json.dumps(mock_manifest)):
                with patch('chunk_jobs.upload_json') as mock_upload:
                    chunk_jobs.main()
                    mock_upload.assert_called_once()
                    # Verify chunk_id is used
                    call_args = mock_upload.call_args
                    uploaded_data = call_args[0][2]
                    assert uploaded_data["chunkId"] == 5


class TestCoverJobEdgeCases:
    """Additional tests for cover_job.py"""
    
    def test_main_without_user_prompt(self):
        """Test cover_job main function without userPrompt"""
        mock_manifest = {
            "storyId": "test-story-123"
        }
        
        with patch('cover_job.parse_args') as mock_args:
            mock_args.return_value.story_id = "test-story-123"
            
            with patch('cover_job.download_text', return_value=json.dumps(mock_manifest)):
                with patch('cover_job.upload_json') as mock_upload:
                    cover_job.main()
                    mock_upload.assert_called_once()
                    call_args = mock_upload.call_args
                    uploaded_data = call_args[0][2]
                    assert uploaded_data["title"] == "Untitled"


class TestFinalAssemblyJobEdgeCases:
    """Additional tests for final_assembly_job.py"""
    
    def test_main_no_chunks(self):
        """Test final_assembly_job main function with no chunks"""
        mock_manifest = {
            "storyId": "test-story-123",
            "genre": "fantasy",
            "readingLevel": "A1"
        }
        
        mock_cover = {
            "storyId": "test-story-123",
            "title": "Test Story",
            "coverUrl": "https://test.com/cover.png"
        }
        
        with patch('final_assembly_job.parse_args') as mock_args:
            mock_args.return_value.story_id = "test-story-123"
            
            with patch('final_assembly_job.download_text') as mock_download:
                mock_download.side_effect = [
                    json.dumps(mock_manifest),
                    json.dumps(mock_cover),
                    Exception("No chunks")
                ]
                
                with patch('final_assembly_job.upload_json') as mock_upload:
                    final_assembly_job.main()
                    mock_upload.assert_called_once()
                    call_args = mock_upload.call_args
                    uploaded_data = call_args[0][2]
                    assert uploaded_data["content"] == []
    
    def test_main_multiple_chunks(self):
        """Test final_assembly_job main function with multiple chunks"""
        mock_manifest = {
            "storyId": "test-story-123",
            "genre": "fantasy",
            "readingLevel": "A1"
        }
        
        mock_cover = {
            "storyId": "test-story-123",
            "title": "Test Story",
            "coverUrl": "https://test.com/cover.png"
        }
        
        mock_chunk1 = {"content": "Chunk 1 content"}
        mock_chunk2 = {"content": "Chunk 2 content"}
        mock_chunk3 = {"content": "Chunk 3 content"}
        
        with patch('final_assembly_job.parse_args') as mock_args:
            mock_args.return_value.story_id = "test-story-123"
            
            with patch('final_assembly_job.download_text') as mock_download:
                mock_download.side_effect = [
                    json.dumps(mock_manifest),
                    json.dumps(mock_cover),
                    json.dumps(mock_chunk1),
                    json.dumps(mock_chunk2),
                    json.dumps(mock_chunk3),
                    Exception("No more chunks")
                ]
                
                with patch('final_assembly_job.upload_json') as mock_upload:
                    final_assembly_job.main()
                    mock_upload.assert_called_once()
                    call_args = mock_upload.call_args
                    uploaded_data = call_args[0][2]
                    assert len(uploaded_data["content"]) == 3

