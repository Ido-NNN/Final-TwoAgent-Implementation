from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
# from twoagentimplement.tools.code_executor import ExecutePythonCodeTool
from crewai_tools import CodeInterpreterTool
#from crewai_tools import FileWriterTool

code_interpreter = CodeInterpreterTool(unsafe_mode=False, default_image_tag='my-fenics-image:latest')

@CrewBase
class PythonProblemSolverCrew:
    """PythonProblemSolverCrew: A two-agent system for solving dynamic Python problems."""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def manager_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['manager_agent'],  # defined in agents.yaml
            verbose=True,
            allow_delegation=True,
            #allow_code_execution=True,
            # code_execution_mode='safe',
            # reasoning=False,
            max_iter=15,
            tools=[code_interpreter],
        
        )

    @agent
    def assistant_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['assistant_agent'],  # defined in agents.yaml
            verbose=True,
            allow_delegation=False,
            # allow_code_execution=True,
            #code_execution_mode='safe',
            # reasoning=True,
            max_iter=15,
        )

    @task
    def problem_solving_task(self) -> Task:
        return Task(
            config=self.tasks_config['problem_solving_task'],  # defined in tasks.yaml
            # context=[self.code_development_task()],
            output_file='output/report.md',
        )

    @task
    def code_development_task(self) -> Task:
        return Task(
            config=self.tasks_config['code_development_task'],  # defined in tasks.yaml
        )
    
    # @task
    # def code_execution_task(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['code_execution_task'],
    #         # context=[self.problem_solving_task()],
    #         output_file='output/report.md',
    #     )

    @crew
    def crew(self) -> Crew:
        """Creates the PythonProblemSolverCrew"""
        return Crew(
            # agents=[self.assistant_agent()],
            agents=self.agents,
            # tasks=self.tasks,
            # process=Process.hierarchical,  # Manager oversees, assistant executes
            # manager_agent=self.manager_agent(),
            # memory=True,
            tasks=[self.problem_solving_task()],
            verbose=True,
            output_log_file='my_crew_log.json',
            cache=False,
            memory=True,
        )
    # crew.reset_memories(command_type='long')      # Clear long-term memory
    # crew.reset_memories(command_type='entity')    # Clear entity memory
    # crew.reset_memories(command_type='knowledge') # Clear knowledge storage
    
    



    

    

     
