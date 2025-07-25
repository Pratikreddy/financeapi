import os
import json
from typing import Tuple, List, Any, Optional
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
import tiktoken
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from llm_agent.prompts_multi import SIMPLE_PROMPT
from llm_agent.tools_multi import generate_pinescript

# ─────────── CONFIG ───────────
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

# ─────────── MEMORY ───────────
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# ─────────── LLM ───────────
llm = AzureChatOpenAI(
    azure_deployment=AZURE_OPENAI_DEPLOYMENT,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    openai_api_version=AZURE_OPENAI_API_VERSION,
    temperature=0,
    response_format={"type": "json_object"},
)

# ─────────── SIMPLE AGENT ───────────
agent = create_openai_tools_agent(
    llm=llm,
    tools=[generate_pinescript],
    prompt=SIMPLE_PROMPT,
)

executor = AgentExecutor(
    agent=agent,
    tools=[generate_pinescript],
    memory=memory,
    verbose=True,
    max_iterations=3,
    return_intermediate_steps=True,
)

# ─────────── MAIN FUNCTION ───────────
def run_pinescript_agent(
    user_input: str, 
    use_multi: bool = True
) -> Tuple[str, int, float, List[Any], List[Any]]:
    """Trading strategy chat with PineScript generation"""
    
    # Run the agent
    result = executor.invoke({"input": user_input})
    
    # Get the output - should already be JSON
    output = result["output"]
    
    # Verify and enhance the JSON response
    try:
        parsed = json.loads(output)
        
        # Ensure all required fields exist for PineScript response
        if "answer" not in parsed:
            parsed["answer"] = output  # Fallback if not proper format
        # Removed document-specific fields (relevant_chunks, display_images, sources_used)
        # These are not needed for PineScript trading assistant
        
        # Try to extract additional metadata from intermediate steps
        intermediate_results = result.get("intermediate_steps", [])
        for action, observation in intermediate_results:
            if action.tool == "generate_pinescript":
                try:
                    pinescript_data = json.loads(observation)
                    if "pinescript_code" in pinescript_data and not parsed.get("pinescript_code"):
                        parsed["pinescript_code"] = pinescript_data["pinescript_code"]
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error processing PineScript results: {e}")
        
        json_str = json.dumps(parsed)
        
    except json.JSONDecodeError:
        # If it's not valid JSON, wrap it for PineScript response
        response = {
            "answer": output
            # Removed document-specific fields not needed for PineScript assistant
        }
        json_str = json.dumps(response)
    
    # Return response
    return json_str, 0, 0.0, memory.buffer, []

def clear_conversation_memory():
    """Clear memory"""
    memory.clear()

# Backwards compatibility - old function name (DEPRECATED)
def run_multi_collection_retrieval(user_input: str, use_multi: bool = True, **kwargs):
    """DEPRECATED: Use run_pinescript_agent instead"""
    return run_pinescript_agent(user_input, use_multi)

# REMOVED - Document search metadata extraction not needed for PineScript app
# def extract_search_metadata(intermediate_steps: List[Any]) -> dict:
#     """Extract metadata from search results for debugging"""
#     metadata = {
#         "collections_searched": [],
#         "total_chunks_found": 0,
#         "sources_found": [],
#         "images_found": [],
#         "tables_found": []
#     }
#     
#     for action, observation in intermediate_steps:
#         if action.tool == "milvus_search_multi":
#             try:
#                 search_data = json.loads(observation)
#                 if "results" in search_data:
#                     metadata["collections_searched"] = search_data.get("collections_searched", [])
#                     metadata["total_chunks_found"] = len(search_data["results"])
#                     
#                     for result in search_data["results"]:
#                         if result.get("chunk_display"):
#                             source = result["chunk_display"]
#                             if source not in metadata["sources_found"]:
#                                 metadata["sources_found"].append(source)
#                         
#                         metadata["images_found"].extend(result.get("chunk_image_paths", []))
#                         metadata["images_found"].extend(result.get("page_images", []))
#                         metadata["tables_found"].extend(result.get("chunk_table_paths", []))
#                         metadata["tables_found"].extend(result.get("page_tables", []))
#                     
#                     # Remove duplicates
#                     metadata["images_found"] = list(set(metadata["images_found"]))
#                     metadata["tables_found"] = list(set(metadata["tables_found"]))
#                     
#             except (json.JSONDecodeError, KeyError) as e:
#                 print(f"Error extracting search metadata: {e}")
#     
#     return metadata