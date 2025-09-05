import pytest
from valkey import ResponseError
from valkey.client import Valkey
from valkey_search_test_case import ValkeySearchTestCaseBase
from valkeytestframework.conftest import resource_port_tracker

"""
This file contains integration tests for FT.INFO command.
Tests the FT.INFO command with various index configurations and data scenarios,
similar to the comprehensive tests in test_fulltext.py.
"""

def _parse_info_kv_list(reply):
    """Helper function to parse FT.INFO response into a dictionary."""
    it = iter(reply)
    out = {}
    for k in it:
        v = next(it, None)
        out[k.decode() if isinstance(k, bytes) else k] = v.decode() if isinstance(v, bytes) else v
    return out

class TestFTInfoIntegration(ValkeySearchTestCaseBase):

    def test_ft_info_basic_text_index(self):
        """
        Test FT.INFO with a basic text index, similar to test_fulltext.py structure.
        """
        client: Valkey = self.server.get_new_client()
        
        # Create a text index similar to test_fulltext.py
        index_name = "products"
        assert client.execute_command(
            "FT.CREATE", index_name,
            "ON", "HASH", 
            "PREFIX", "1", "product:",
            "SCHEMA", "desc", "TEXT"
        ) == b"OK"
        
        # Get info before adding any documents
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        
        # Verify basic index structure
        assert info["index_name"] == index_name
        assert info["key_type"] == "HASH"
        assert info["prefixes"] == ["product:"]
        assert info["num_docs"] == 0
        assert info["num_terms"] == 0
        assert info["num_records"] == 0
        
        # Verify attributes structure for TEXT field
        attributes = info["attributes"]
        assert len(attributes) == 1
        text_attr = _parse_info_kv_list(attributes[0])
        assert text_attr["identifier"] == "desc"
        assert text_attr["attribute"] == "desc"
        assert text_attr["type"] == "TEXT"
        
        # Add some documents like in test_fulltext.py
        docs = [
            ["HSET", "product:1", "desc", "great laptop"],
            ["HSET", "product:2", "desc", "good tablet"],
            ["HSET", "product:3", "desc", "wonder phone"]
        ]
        
        for doc in docs:
            assert client.execute_command(*doc) == 2
        
        # Get info after adding documents
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        
        # Verify document counts have increased
        assert info["num_docs"] == 3
        assert info["num_terms"] > 0  # Should have indexed terms
        assert info["num_records"] > 0  # Should have records

    def test_ft_info_text_index_with_options(self):
        """
        Test FT.INFO with text index using various options like STOPWORDS, NOSTEM, etc.
        """
        client: Valkey = self.server.get_new_client()
        
        # Create text index with options similar to test_fulltext.py
        index_name = "products_advanced"
        assert client.execute_command(
            "FT.CREATE", index_name,
            "ON", "HASH",
            "PREFIX", "1", "product:",
            "STOPWORDS", "2", "the", "and",
            "NOSTEM",
            "WITHOFFSETS",
            "PUNCTUATION", ".,!?",
            "SCHEMA", "content", "TEXT"
        ) == b"OK"
        
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        
        # Verify index-level options are reflected in info
        assert info["stop_words"] == ["the", "and"]
        assert info["with_offsets"] == "1"
        assert info["punctuation"] == ".,!?"
        
        # Verify TEXT attribute shows NOSTEM
        attributes = info["attributes"]
        text_attr = _parse_info_kv_list(attributes[0])
        assert text_attr["type"] == "TEXT"
        # NOSTEM should be reflected in the attribute info
        assert "NO_STEM" in text_attr or text_attr.get("NO_STEM") == "1"

    def test_ft_info_multiple_field_types(self):
        """
        Test FT.INFO with mixed field types (TEXT, NUMERIC, TAG, VECTOR).
        """
        client: Valkey = self.server.get_new_client()
        
        index_name = "mixed_index"
        assert client.execute_command(
            "FT.CREATE", index_name,
            "ON", "HASH",
            "PREFIX", "1", "item:",
            "SCHEMA", 
            "description", "TEXT",
            "price", "NUMERIC",
            "tags", "TAG", "SEPARATOR", ",",
            "embedding", "VECTOR", "FLAT", "6", "DIM", "128", "DISTANCE_METRIC", "COSINE", "TYPE", "FLOAT32"
        ) == b"OK"
        
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        
        # Verify we have 4 attributes
        attributes = info["attributes"]
        assert len(attributes) == 4
        
        # Parse each attribute and verify types
        attr_types = {}
        for attr_data in attributes:
            attr = _parse_info_kv_list(attr_data)
            attr_types[attr["identifier"]] = attr["type"]
        
        assert attr_types["description"] == "TEXT"
        assert attr_types["price"] == "NUMERIC"
        assert attr_types["tags"] == "TAG"
        assert attr_types["embedding"] == "VECTOR"
        
        # Verify TAG separator
        for attr_data in attributes:
            attr = _parse_info_kv_list(attr_data)
            if attr["identifier"] == "tags":
                assert attr["SEPARATOR"] == ","
                break
        
        # Verify VECTOR configuration
        for attr_data in attributes:
            attr = _parse_info_kv_list(attr_data)
            if attr["identifier"] == "embedding":
                assert attr["algorithm"] == "FLAT"
                assert attr["dim"] == 128
                assert attr["distance_metric"] == "COSINE"
                assert attr["data_type"] == "FLOAT32"
                break

    def test_ft_info_with_data_indexing(self):
        """
        Test FT.INFO shows correct statistics after indexing real data.
        """
        client: Valkey = self.server.get_new_client()
        
        # Create index similar to test_fulltext.py
        index_name = "test_stats"
        assert client.execute_command(
            "FT.CREATE", index_name,
            "ON", "HASH",
            "PREFIX", "1", "doc:",
            "SCHEMA", "content", "TEXT", "score", "NUMERIC"
        ) == b"OK"
        
        # Add documents with varied content
        docs = [
            ["HSET", "doc:1", "content", "the quick brown fox jumps", "score", "95"],
            ["HSET", "doc:2", "content", "over the lazy dog sleeping", "score", "87"],
            ["HSET", "doc:3", "content", "in the sunny garden today", "score", "92"],
            ["HSET", "doc:4", "content", "quick search results found", "score", "88"],
            ["HSET", "doc:5", "content", "brown fox running fast", "score", "90"]
        ]
        
        for doc in docs:
            assert client.execute_command(*doc) == 3
        
        # Get info and verify statistics
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        
        # Should have indexed all documents
        assert info["num_docs"] == 5
        
        # Should have multiple terms (words from the content)
        assert info["num_terms"] > 10  # We have many unique words
        
        # Should have records for both TEXT and NUMERIC fields
        assert info["num_records"] >= 10  # At least 5 docs * 2 fields
        
        # Verify no indexing failures
        assert info["hash_indexing_failures"] == "0"
        
        # Verify index is ready
        assert info["state"] == "ready"

    def test_ft_info_per_field_search_integration(self):
        """
        Test FT.INFO with multiple text fields and verify field-specific indexing.
        Similar to test_text_search_per_field in test_fulltext.py.
        """
        client: Valkey = self.server.get_new_client()
        
        # Create index with multiple text fields
        index_name = "multi_text"
        assert client.execute_command(
            "FT.CREATE", index_name,
            "ON", "HASH",
            "PREFIX", "1", "product:",
            "SCHEMA", "title", "TEXT", "description", "TEXT"
        ) == b"OK"
        
        # Add documents similar to test_fulltext.py
        docs = [
            ["HSET", "product:1", "title", "Great Laptop", "description", "wonder experience here"],
            ["HSET", "product:2", "title", "Good Tablet", "description", "Hello, where are you"],
            ["HSET", "product:3", "title", "Ok Phone", "description", "Hello, how are you"],
            ["HSET", "product:4", "title", "wonder Book", "description", "Hello, what are you doing Great"]
        ]
        
        for doc in docs:
            assert client.execute_command(*doc) == 3
        
        # Test field-specific searches work
        result_title = client.execute_command("FT.SEARCH", index_name, '@title:"wonder"')
        assert result_title[0] == 1  # Should find product:4
        
        result_desc = client.execute_command("FT.SEARCH", index_name, '@description:"wonder"')
        assert result_desc[0] == 1  # Should find product:1
        
        # Get info and verify both fields are indexed
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        
        # Should have 2 TEXT attributes
        attributes = info["attributes"]
        assert len(attributes) == 2
        
        text_fields = []
        for attr_data in attributes:
            attr = _parse_info_kv_list(attr_data)
            if attr["type"] == "TEXT":
                text_fields.append(attr["identifier"])
        
        assert "title" in text_fields
        assert "description" in text_fields
        
        # Should have indexed terms from both fields
        assert info["num_docs"] == 4
        assert info["num_terms"] > 8  # Multiple unique terms across both fields

    def test_ft_info_error_cases(self):
        """
        Test FT.INFO error handling similar to test_fulltext.py error patterns.
        """
        client: Valkey = self.server.get_new_client()
        
        # Test non-existent index
        with pytest.raises(ResponseError) as exc_info:
            client.execute_command("FT.INFO", "nonexistent_index")
        assert "not found" in str(exc_info.value)
        
        # Test wrong number of arguments
        with pytest.raises(ResponseError) as exc_info:
            client.execute_command("FT.INFO")
        assert "wrong number of arguments" in str(exc_info.value)
        
        # Create an index and then test valid info
        assert client.execute_command(
            "FT.CREATE", "test_index",
            "ON", "HASH",
            "SCHEMA", "field", "TEXT"
        ) == b"OK"
        
        # This should work
        info_reply = client.execute_command("FT.INFO", "test_index")
        info = _parse_info_kv_list(info_reply)
        assert info["index_name"] == "test_index"

    def test_ft_info_custom_stopwords_integration(self):
        """
        Test FT.INFO shows custom stopwords configuration and verify they work in search.
        Similar to test_custom_stopwords in test_fulltext.py.
        """
        client: Valkey = self.server.get_new_client()
        
        # Create index with custom stopwords
        index_name = "custom_stop"
        assert client.execute_command(
            "FT.CREATE", index_name,
            "ON", "HASH",
            "STOPWORDS", "2", "the", "and",
            "SCHEMA", "content", "TEXT"
        ) == b"OK"
        
        # Verify stopwords in info
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        assert info["stop_words"] == ["the", "and"]
        
        # Add document and test that stopwords are actually filtered
        assert client.execute_command("HSET", "doc:1", "content", "the cat and dog are good") == 2
        
        # Search for stopword should return no results
        result = client.execute_command("FT.SEARCH", index_name, '@content:"and"')
        assert result[0] == 0  # Stop word filtered out
        
        # Search for non-stopword should work
        result = client.execute_command("FT.SEARCH", index_name, '@content:"cat"')
        assert result[0] == 1  # Regular word indexed

    def test_ft_info_nostem_integration(self):
        """
        Test FT.INFO shows NOSTEM configuration and verify it works in search.
        Similar to test_nostem in test_fulltext.py.
        """
        client: Valkey = self.server.get_new_client()
        
        # Create index with NOSTEM
        index_name = "nostem_test"
        assert client.execute_command(
            "FT.CREATE", index_name,
            "ON", "HASH",
            "NOSTEM",
            "SCHEMA", "content", "TEXT"
        ) == b"OK"
        
        # Verify NOSTEM in info
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        
        # Check that NOSTEM is reflected in the attributes
        attributes = info["attributes"]
        text_attr = _parse_info_kv_list(attributes[0])
        assert text_attr["type"] == "TEXT"
        # NOSTEM should be indicated in the attribute info
        assert "NO_STEM" in text_attr or text_attr.get("NO_STEM") == "1"
        
        # Add document and test exact form matching
        assert client.execute_command("HSET", "doc:1", "content", "running quickly") == 2
        
        # With NOSTEM, exact forms should be findable
        result = client.execute_command("FT.SEARCH", index_name, '@content:"running"')
        assert result[0] == 1  # Exact form found

    def test_ft_info_punctuation_integration(self):
        """
        Test FT.INFO shows punctuation configuration and verify tokenization works.
        Similar to test_custom_punctuation in test_fulltext.py.
        """
        client: Valkey = self.server.get_new_client()
        
        # Create index with custom punctuation
        index_name = "punct_test"
        assert client.execute_command(
            "FT.CREATE", index_name,
            "ON", "HASH",
            "PUNCTUATION", ".",
            "SCHEMA", "content", "TEXT"
        ) == b"OK"
        
        # Verify punctuation in info
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        assert info["punctuation"] == "."
        
        # Add document and test that punctuation separates tokens
        assert client.execute_command("HSET", "doc:1", "content", "hello.world test@email") == 2
        
        # Dot configured as separator - should find split words
        result = client.execute_command("FT.SEARCH", index_name, '@content:"hello"')
        assert result[0] == 1  # Found "hello" as separate token
        
        # @ NOT configured as separator - should not find split words
        result = client.execute_command("FT.SEARCH", index_name, '@content:"test"')
        assert result[0] == 0  # "test" not separated from "@email"

    def test_ft_info_tag_field_integration(self):
        """
        Test FT.INFO with TAG fields and verify separator configuration.
        """
        client: Valkey = self.server.get_new_client()
        
        # Create index with TAG field
        index_name = "tag_test"
        assert client.execute_command(
            "FT.CREATE", index_name,
            "ON", "HASH",
            "SCHEMA", "categories", "TAG", "SEPARATOR", "|"
        ) == b"OK"
        
        # Verify TAG configuration in info
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        
        attributes = info["attributes"]
        tag_attr = _parse_info_kv_list(attributes[0])
        assert tag_attr["type"] == "TAG"
        assert tag_attr["SEPARATOR"] == "|"
        
        # Add document with tags
        assert client.execute_command("HSET", "doc:1", "categories", "electronics|gadgets|mobile") == 2
        
        # Search for individual tags should work
        result = client.execute_command("FT.SEARCH", index_name, '@categories:{electronics}')
        assert result[0] == 1
        
        result = client.execute_command("FT.SEARCH", index_name, '@categories:{gadgets}')
        assert result[0] == 1

    def test_ft_info_numeric_field_integration(self):
        """
        Test FT.INFO with NUMERIC fields and verify range queries work.
        """
        client: Valkey = self.server.get_new_client()
        
        # Create index with NUMERIC field
        index_name = "numeric_test"
        assert client.execute_command(
            "FT.CREATE", index_name,
            "ON", "HASH",
            "SCHEMA", "price", "NUMERIC", "rating", "NUMERIC"
        ) == b"OK"
        
        # Verify NUMERIC configuration in info
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        
        attributes = info["attributes"]
        assert len(attributes) == 2
        
        for attr_data in attributes:
            attr = _parse_info_kv_list(attr_data)
            assert attr["type"] == "NUMERIC"
            assert attr["identifier"] in ["price", "rating"]
        
        # Add documents with numeric values
        docs = [
            ["HSET", "item:1", "price", "100", "rating", "4.5"],
            ["HSET", "item:2", "price", "200", "rating", "3.8"],
            ["HSET", "item:3", "price", "150", "rating", "4.2"]
        ]
        
        for doc in docs:
            assert client.execute_command(*doc) == 3
        
        # Test numeric range queries
        result = client.execute_command("FT.SEARCH", index_name, '@price:[100 150]')
        assert result[0] == 2  # Should find items 1 and 3
        
        result = client.execute_command("FT.SEARCH", index_name, '@rating:[4.0 5.0]')
        assert result[0] == 2  # Should find items 1 and 3

    def test_ft_info_comprehensive_stats(self):
        """
        Test FT.INFO provides comprehensive statistics after complex indexing operations.
        """
        client: Valkey = self.server.get_new_client()
        
        # Create comprehensive index
        index_name = "comprehensive"
        assert client.execute_command(
            "FT.CREATE", index_name,
            "ON", "HASH",
            "PREFIX", "1", "item:",
            "STOPWORDS", "1", "the",
            "SCHEMA", 
            "title", "TEXT",
            "description", "TEXT", "NOSTEM",
            "price", "NUMERIC",
            "tags", "TAG"
        ) == b"OK"
        
        # Add many documents to generate meaningful statistics
        for i in range(20):
            assert client.execute_command(
                "HSET", f"item:{i}",
                "title", f"Product {i} the best",
                "description", f"Description for product {i} running fast",
                "price", str(100 + i * 10),
                "tags", f"category{i % 3},type{i % 2}"
            ) == 5
        
        # Get comprehensive info
        info_reply = client.execute_command("FT.INFO", index_name)
        info = _parse_info_kv_list(info_reply)
        
        # Verify comprehensive statistics
        assert info["num_docs"] == 20
        assert int(info["num_terms"]) > 30  # Many unique terms
        assert int(info["num_records"]) >= 80  # 20 docs * 4 fields
        assert info["hash_indexing_failures"] == "0"
        assert info["state"] == "ready"
        
        # Verify all field types are present
        attributes = info["attributes"]
        assert len(attributes) == 4
        
        field_types = {}
        for attr_data in attributes:
            attr = _parse_info_kv_list(attr_data)
            field_types[attr["identifier"]] = attr["type"]
        
        assert field_types["title"] == "TEXT"
        assert field_types["description"] == "TEXT"
        assert field_types["price"] == "NUMERIC"
        assert field_types["tags"] == "TAG"
        
        # Verify stopwords configuration
        assert info["stop_words"] == ["the"]
        
        # Verify searches still work correctly
        result = client.execute_command("FT.SEARCH", index_name, '@title:"Product"')
        assert result[0] == 20  # All products should match
        
        result = client.execute_command("FT.SEARCH", index_name, '@price:[100 150]')
        assert result[0] == 6  # Products 0-5 should match
