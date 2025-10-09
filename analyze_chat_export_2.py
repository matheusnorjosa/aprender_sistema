#!/usr/bin/env python3
"""
MCP File Processing Tool Test - Chat Export Analysis
Testing analyze_file_structure and process_large_json on temp_chat_export_2.json
"""

import json
import os
import time
from pathlib import Path


def analyze_file_structure(file_path):
    """Analyze the structure of a JSON file efficiently"""
    results = {
        "file_info": {},
        "structure_analysis": {},
        "sample_data": {},
        "performance_metrics": {},
    }

    start_time = time.time()

    # File basic info
    if os.path.exists(file_path):
        file_stats = os.stat(file_path)
        results["file_info"] = {
            "size_bytes": file_stats.st_size,
            "size_mb": round(file_stats.st_size / (1024 * 1024), 2),
            "exists": True,
            "path": str(file_path),
        }
    else:
        results["file_info"] = {"exists": False}
        return results

    # Analyze structure
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            # Read first few characters to determine structure
            first_chars = f.read(100)
            f.seek(0)

            if first_chars.strip().startswith("["):
                # Array format - load and analyze
                data = json.load(f)

                if isinstance(data, list):
                    results["structure_analysis"] = {
                        "type": "array",
                        "length": len(data),
                        "first_item_type": (
                            type(data[0]).__name__ if data else "unknown"
                        ),
                    }

                    # Analyze first item if it's a dict
                    if data and isinstance(data[0], dict):
                        first_item = data[0]
                        results["structure_analysis"]["first_item_keys"] = list(
                            first_item.keys()
                        )

                        # Chat-specific analysis
                        if "chat" in first_item and isinstance(
                            first_item["chat"], dict
                        ):
                            chat = first_item["chat"]
                            results["structure_analysis"]["chat_structure"] = {
                                "has_chat": True,
                                "chat_keys": list(chat.keys()),
                                "has_history": "history" in chat,
                                "has_messages": "history" in chat
                                and "messages" in chat["history"],
                            }

                            # Count messages if present
                            if chat.get("history", {}).get("messages"):
                                messages = chat["history"]["messages"]
                                message_count = len(messages)
                                results["structure_analysis"][
                                    "message_count"
                                ] = message_count

                                # Analyze message types
                                roles = []
                                for msg_id, msg in messages.items():
                                    if isinstance(msg, dict) and "role" in msg:
                                        roles.append(msg["role"])

                                results["structure_analysis"]["roles_found"] = list(
                                    set(roles)
                                )
                                results["structure_analysis"]["role_distribution"] = {
                                    role: roles.count(role) for role in set(roles)
                                }

                        # Sample data (first chat only, truncated)
                        sample_item = dict(first_item)
                        if "chat" in sample_item and "history" in sample_item["chat"]:
                            # Truncate messages for sampling
                            if "messages" in sample_item["chat"]["history"]:
                                messages = sample_item["chat"]["history"]["messages"]
                                if len(messages) > 2:
                                    # Keep only first 2 messages for sample
                                    first_two_keys = list(messages.keys())[:2]
                                    sample_item["chat"]["history"]["messages"] = {
                                        k: messages[k] for k in first_two_keys
                                    }
                                    sample_item["chat"]["history"][
                                        "_truncated"
                                    ] = f"Showing 2 of {len(messages)} messages"

                        results["sample_data"] = {"first_chat_sample": sample_item}

            elif first_chars.strip().startswith("{"):
                # Object format
                data = json.load(f)
                results["structure_analysis"] = {
                    "type": "object",
                    "keys": list(data.keys()) if isinstance(data, dict) else "unknown",
                }

    except Exception as e:
        results["structure_analysis"] = {"error": str(e)}

    end_time = time.time()
    results["performance_metrics"] = {
        "processing_time_seconds": round(end_time - start_time, 3)
    }

    return results


def process_large_json_chunked(file_path, chunk_method="messages"):
    """Process large JSON file using chunking method"""
    results = {
        "processing_info": {},
        "chunk_analysis": {},
        "content_summary": {},
        "performance_metrics": {},
    }

    start_time = time.time()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        results["processing_info"] = {
            "method": f"chunking_by_{chunk_method}",
            "file_loaded": True,
            "data_type": type(data).__name__,
        }

        if isinstance(data, list) and data:
            total_chats = len(data)
            results["chunk_analysis"] = {
                "total_chats": total_chats,
                "chunks_processed": 0,
                "total_messages": 0,
                "content_types": set(),
                "models_used": set(),
                "file_attachments": 0,
                "conversation_topics": [],
            }

            # Process each chat (chunk)
            for i, chat_export in enumerate(data):
                if isinstance(chat_export, dict):
                    # Extract chat title
                    title = chat_export.get("title", f"Chat {i+1}")
                    results["chunk_analysis"]["conversation_topics"].append(title)

                    # Count models
                    if "chat" in chat_export and "models" in chat_export["chat"]:
                        models = chat_export["chat"]["models"]
                        results["chunk_analysis"]["models_used"].update(models)

                    # Process messages
                    if (
                        "chat" in chat_export
                        and "history" in chat_export["chat"]
                        and "messages" in chat_export["chat"]["history"]
                    ):

                        messages = chat_export["chat"]["history"]["messages"]
                        results["chunk_analysis"]["total_messages"] += len(messages)

                        # Analyze message content
                        for msg_id, msg in messages.items():
                            if isinstance(msg, dict):
                                # Check for files
                                if "files" in msg and msg["files"]:
                                    results["chunk_analysis"][
                                        "file_attachments"
                                    ] += len(msg["files"])

                                # Track content types
                                if "content" in msg:
                                    content = msg["content"]
                                    if '<details type="reasoning"' in content:
                                        results["chunk_analysis"]["content_types"].add(
                                            "reasoning"
                                        )
                                    if "Sistema APRENDER" in content:
                                        results["chunk_analysis"]["content_types"].add(
                                            "system_analysis"
                                        )
                                    if len(content) > 1000:
                                        results["chunk_analysis"]["content_types"].add(
                                            "long_form"
                                        )

                        results["chunk_analysis"]["chunks_processed"] += 1

                        # Limit processing for performance (process first 5 chats)
                        if i >= 4:
                            results["chunk_analysis"]["processing_limited"] = True
                            break

            # Convert sets to lists for JSON serialization
            results["chunk_analysis"]["content_types"] = list(
                results["chunk_analysis"]["content_types"]
            )
            results["chunk_analysis"]["models_used"] = list(
                results["chunk_analysis"]["models_used"]
            )

            # Summary
            results["content_summary"] = {
                "chat_export_type": "AI Assistant Conversations",
                "primary_topics": results["chunk_analysis"]["conversation_topics"][:5],
                "total_conversations": total_chats,
                "avg_messages_per_chat": round(
                    results["chunk_analysis"]["total_messages"]
                    / max(results["chunk_analysis"]["chunks_processed"], 1),
                    1,
                ),
                "has_file_attachments": results["chunk_analysis"]["file_attachments"]
                > 0,
                "has_reasoning_traces": "reasoning"
                in results["chunk_analysis"]["content_types"],
            }

    except Exception as e:
        results["processing_info"]["error"] = str(e)

    end_time = time.time()
    results["performance_metrics"] = {
        "processing_time_seconds": round(end_time - start_time, 3)
    }

    return results


def main():
    file_path = "temp_chat_export_2.json"

    print("=" * 60)
    print("MCP FILE PROCESSING TOOL TEST")
    print("=" * 60)
    print(f"Testing file: {file_path}")
    print()

    # Test 1: analyze_file_structure
    print("1. TESTING analyze_file_structure()")
    print("-" * 40)
    structure_result = analyze_file_structure(file_path)
    print(json.dumps(structure_result, indent=2, default=str))
    print()

    # Test 2: process_large_json with chunking
    print("2. TESTING process_large_json() with chunking")
    print("-" * 40)
    chunked_result = process_large_json_chunked(file_path, "messages")
    print(json.dumps(chunked_result, indent=2, default=str))
    print()

    # Analysis comparison
    print("3. ANALYSIS COMPARISON")
    print("-" * 40)
    print("File Structure Analysis:")
    print(
        f"  - File size: {structure_result.get('file_info', {}).get('size_mb', 'unknown')} MB"
    )
    print(
        f"  - Processing time: {structure_result.get('performance_metrics', {}).get('processing_time_seconds', 'unknown')} seconds"
    )
    print(
        f"  - Structure type: {structure_result.get('structure_analysis', {}).get('type', 'unknown')}"
    )
    print(
        f"  - Array length: {structure_result.get('structure_analysis', {}).get('length', 'unknown')}"
    )
    print()

    print("Chunked Processing Analysis:")
    print(
        f"  - Processing time: {chunked_result.get('performance_metrics', {}).get('processing_time_seconds', 'unknown')} seconds"
    )
    print(
        f"  - Total chats: {chunked_result.get('chunk_analysis', {}).get('total_chats', 'unknown')}"
    )
    print(
        f"  - Total messages: {chunked_result.get('chunk_analysis', {}).get('total_messages', 'unknown')}"
    )
    print(
        f"  - Content types: {chunked_result.get('chunk_analysis', {}).get('content_types', [])}"
    )
    print(
        f"  - Models used: {chunked_result.get('chunk_analysis', {}).get('models_used', [])}"
    )
    print()

    print("4. CHAT EXPORT INSIGHTS")
    print("-" * 40)
    content_summary = chunked_result.get("content_summary", {})
    print(f"Export Type: {content_summary.get('chat_export_type', 'Unknown')}")
    print(f"Conversation Topics:")
    for topic in content_summary.get("primary_topics", []):
        print(f"  - {topic}")
    print(
        f"Average Messages per Chat: {content_summary.get('avg_messages_per_chat', 'unknown')}"
    )
    print(f"Has File Attachments: {content_summary.get('has_file_attachments', False)}")
    print(f"Has Reasoning Traces: {content_summary.get('has_reasoning_traces', False)}")


if __name__ == "__main__":
    main()
