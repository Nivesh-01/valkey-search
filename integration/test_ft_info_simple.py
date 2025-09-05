import pytest
from valkey import ResponseError
from valkey.client import Valkey
from valkey_search_test_case import ValkeySearchTestCaseBase

"""
Simple test to verify FT.INFO integration test structure works.
"""

def _parse_info_kv_list(reply):
    """Helper function to parse FT.INFO response into a dictionary."""
    it = iter(reply)
    out = {}
    for k in it:
        v = next(it, None)
        out[k.decode() if isinstance(k, bytes) else k] = v.decode() if isinstance(v, bytes) else v
    return out

class TestFTInfoSimple(ValkeySearchTestCaseBase):

    def test_ft_info_basic_functionality(self):
        """
        Simple test to verify FT.INFO works with a basic text index.
        """
        client: Valkey = self.server.get_new_client()
        
        # Create a simple text index
        index_name = "simple_test"
        assert client.execute_command(
            "FT.CREATE", index_name,
            "ON", "HASH", 
            "PREFIX", "1", "doc:",
            "SCHEMA", "content", "TEXT"
        ) == b"OK"
        
        # Get info for the index
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        
        # Verify basic structure
        assert info["index_name"] == index_name
        assert info["key_type"] == "HASH"
        assert info["prefixes"] == ["doc:"]
        assert info["num_docs"] == 0
        
        # Verify attributes structure
        attributes = info["attributes"]
        assert len(attributes) == 1
        text_attr = _parse_info_kv_list(attributes[0])
        assert text_attr["identifier"] == "content"
        assert text_attr["type"] == "TEXT"

    def test_ft_info_error_case(self):
        """
        Test FT.INFO error handling for non-existent index.
        """
        client: Valkey = self.server.get_new_client()
        
        # Test non-existent index
        with pytest.raises(ResponseError) as exc_info:
            client.execute_command("FT.INFO", "nonexistent_index")
        assert "not found" in str(exc_info.value)
