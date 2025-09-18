# genai-exchange-trip-planner

Steps to run
1. Open individual terminals for eachagent (6 terminals in total)
2. cd to the individual agent folder (e.g. cd "genai-exchange-trip-planner\backend\trip_planner\agents\sub_agents\booking")
3. In all the individual terminals, run ".venv\scripts\activate" (each agent folder has its own environment created) 
4. Run "uv run --active ." in each of the individual 6 terminals. This will run the server of the individual agents in their respective localhost using uvicorn.
5. For the main host agent: cd to sub_agents folder: "genai-exchange-trip-planner\backend\trip_planner\agents\sub_agents"
6. For the main host agent run: "uv run --active adk web". This will start the application in adk web.
7. Open the ADK web and select agent_host in the top-left side. Start asking queries.