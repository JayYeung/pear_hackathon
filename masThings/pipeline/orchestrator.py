import os
import asyncio
import json
from typing import List, TypedDict, Annotated, Sequence
import operator

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode # Using ToolNode simplifies calling tools

from langchain_mcp_adapters.client import MultiServerMCPClient

# Define the state for the graph
class AgentState(TypedDict):
    messages: Sequence[BaseMessage] # History of messages
    repo_url: str | None           # Input repo URL
    cloned_repo_path: str | None   # Path after successful clone
    scan_results: str | None       # Results from Semgrep scan
    error_message: str | None      # To capture errors during the flow

# --- Main Pipeline Logic --- #

async def run_security_audit_pipeline(repo_url: str) -> str:
    """Runs the security audit pipeline using LangGraph and MCP servers."""

    print(f"Starting security audit for: {repo_url}")

    # --- 1. Define MCP Server Configurations --- #
    # Assumes these scripts are in the ../mcp_servers directory relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    servers_dir = os.path.join(current_dir, '..', 'mcp_servers')

    server_configs = {
        "git_server": {
            "command": "python",
            "args": [os.path.join(servers_dir, "git_mcp_server.py")],
            "transport": "stdio",
            "workdir": os.path.join(current_dir, '..') # Run server from project root
        },
        "semgrep_server": {
            "command": "python",
            "args": [os.path.join(servers_dir, "semgrep_mcp_server.py")],
            "transport": "stdio",
             "workdir": os.path.join(current_dir, '..') # Run server from project root
        },
        # Add other servers here as they are developed
    }

    async with MultiServerMCPClient(connections=server_configs) as client:
        mcp_tools = client.get_tools()
        print(f"MCP Tools discovered: {[tool.name for tool in mcp_tools]}")

        # Check if essential tools are present
        required_tools = {"clone_repository", "run_semgrep_scan"}
        available_tools = {tool.name for tool in mcp_tools}
        if not required_tools.issubset(available_tools):
             missing = required_tools - available_tools
             print(f"Error: Missing required MCP tools: {', '.join(missing)}")
             return f"Error: Missing required MCP tools: {', '.join(missing)}"

        tool_node = ToolNode(mcp_tools) # Node to execute MCP tools

        # --- 2. Initialize LLM --- #
        # Ensure ANTHROPIC_API_KEY is set in your environment
        # Consider adding error handling for missing API key
        try:
            llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0)
            # You can change the model to claude-3-opus-20240229 or claude-3-haiku-20240307 if preferred
        except Exception as e:
            return f"Error initializing LLM: {e}. Is the ANTHROPIC_API_KEY set?"

        # Bind tools to LLM so it knows it can use them
        llm_with_tools = llm.bind_tools(mcp_tools)

        # --- 3. Define Graph Nodes --- #

        # Define the function that determines whether to continue or end
        def should_continue(state: AgentState) -> str:
            messages = state['messages']
            last_message = messages[-1]
            # If the LLM invocation resulted in errors, stop
            if state.get("error_message"):
                print(f"Error occurred: {state['error_message']}. Ending graph.")
                return END
            # If there are no tool calls, finish
            if not last_message.tool_calls:
                 print("No tool calls requested by LLM. Ending graph.")
                 return END
            # Otherwise, continue to execute tools
            return "tools"

        # Define the function that calls the model
        def call_model(state: AgentState):
            messages = state['messages']
            print("\n--- Calling LLM ---")
            response = llm_with_tools.invoke(messages)
            print(f"LLM Response: {response}")
            # We return a list, because this will get added to the existing list
            return {"messages": [response]}

        # --- 4. Define Graph Workflow --- #
        workflow = StateGraph(AgentState)

        # Define the two nodes we will cycle between
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)

        # Set the entrypoint
        workflow.set_entry_point("agent")

        # Add edges: LLM decides if tools are needed, tools return to LLM
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END
            }
        )
        workflow.add_edge("tools", "agent")

        # Compile the graph
        app = workflow.compile()

        # --- 5. Run the Graph --- #
        initial_message = HumanMessage(
            content=f"Perform a security audit on the repository: {repo_url}. "
                    f"First, clone the repository using the 'clone_repository' tool. Then, run a semgrep scan on the cloned path using 'run_semgrep_scan', passing 'auto' as the config argument."
        )
        initial_state = {"messages": [initial_message], "repo_url": repo_url}

        final_state = None
        try:
            print("\n--- Invoking LangGraph App ---")
            async for output in app.astream(initial_state):
                # stream() yields detailed state updates
                # For simplicity here, we'll just capture the final state
                # print(f"\nState Update:")
                # print(output)
                # print("---")
                last_key = list(output.keys())[-1]
                final_state = output[last_key]

            print("\n--- Graph Execution Finished ---")

            if not final_state or not final_state.get('messages'):
                 return "Error: Graph execution finished unexpectedly with no final state."

            # --- 6. Process Final State and Return Summary --- #
            # Find the relevant messages (e.g., tool results, final AI message)
            summary = f"Audit Pipeline Summary for {repo_url}:\n"
            cloned_path = None
            scan_output = None

            for msg in reversed(final_state['messages']):
                if isinstance(msg, ToolMessage):
                    if msg.tool_call_id:
                        # Find the tool call that generated this result
                        tool_call = next((tc for tc in final_state['messages'][-2].tool_calls if tc['id'] == msg.tool_call_id), None)
                        if tool_call:
                            tool_name = tool_call['name']
                            tool_args = tool_call['args']
                            if tool_name == 'clone_repository' and not msg.content.startswith("Error:"):
                                cloned_path = msg.content
                                summary += f"- Repository cloned to: {cloned_path}\n"
                            elif tool_name == 'run_semgrep_scan':
                                try:
                                    scan_data = json.loads(msg.content)
                                    if "error" in scan_data:
                                        summary += f"- Semgrep scan failed: {scan_data['error']}\n"
                                    else:
                                        num_findings = len(scan_data.get("results", []))
                                        scan_output = msg.content # Store raw JSON
                                        summary += f"- Semgrep scan completed. Found {num_findings} potential findings.\n"
                                except json.JSONDecodeError:
                                    summary += f"- Semgrep scan returned non-JSON output: {msg.content[:200]}...\n"
                                except Exception as e:
                                    summary += f"- Error processing Semgrep results: {e}\n"

                elif isinstance(msg, AIMessage) and not msg.tool_calls:
                    summary += f"\nFinal LLM Message: {msg.content}\n"
                    break # Stop once we hit the last non-tool-calling AI message
            
            # Optionally, add raw scan results if needed, or process further
            # summary += f"\nRaw Scan Results (JSON):\n{scan_output if scan_output else 'N/A'}"

            return summary.strip()

        except Exception as e:
            print(f"Error running LangGraph app: {e}")
            import traceback
            traceback.print_exc() # Print stack trace for debugging
            return f"Error during pipeline execution: {e}"

# Example of how to run this (e.g., from the wrapper server)
# if __name__ == "__main__":
#     repo_to_audit = "https://github.com/langchain-ai/langchain" # Example repo
#     # Load .env file if it exists (for API keys)
#     from dotenv import load_dotenv
#     load_dotenv()
#     result = asyncio.run(run_security_audit_pipeline(repo_to_audit))
#     print("\n--- Final Pipeline Result ---")
#     print(result)
