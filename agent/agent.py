from my_agent.graph import build_survey_graph
from core.database import db
# Call the function from graph.py to get the compiled agent
agent = build_survey_graph()

# This file is now set up to be discoverable by the LangGraph CLI
# when running 'langgraph dev' with langgraph.json pointing to 'agent:agent'.