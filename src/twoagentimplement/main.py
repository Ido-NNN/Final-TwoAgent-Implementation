import warnings
import os
import openai
from dotenv import load_dotenv

from twoagentimplement.crew import PythonProblemSolverCrew

# Suppress unnecessary warnings for a cleaner output
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def is_fem_related(problem_description: str) -> bool:
    """
    Uses an LLM to quickly classify if a problem description is related to FEM.

    Args:
        problem_description: The user's input string.

    Returns:
        True if the input is related to FEM, False otherwise.
    """
    # Load environment variables from .env file
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found. Please add it to your .env file.")
        return False

    client = openai.OpenAI()
    prompt = f"""
    Is the following problem description related to the Finite Element Method (FEM),
    computational mechanics, simulations, physics, or engineering analysis?
    Problem: "{problem_description}"

    Analyze the text and answer with only a single word: YES or NO.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert classifier for engineering and physics problems."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=5,
            temperature=0.0
        )
        answer = response.choices[0].message.content.strip().upper()
        print(f"Input validation check returned: {answer}")
        return "YES" in answer
    except Exception as e:
        print(f"An error occurred during LLM validation check: {e}")
        # Default to False to prevent running on an error
        return False

def run():
    """
    Validates the input and then runs the crew if the input is relevant.
    """
    # You can get this input from a user, a file, or hardcode it for testing.
    problem = input()
    
    inputs = {
        "problem_description": problem
    }

    print("\n--- Validating Input ---")
    if is_fem_related(inputs["problem_description"]):
        print("\n--- Input is Relevant ---")
        print("Starting the FEM Problem Solver Crew...")
        try:
            crew_instance = PythonProblemSolverCrew().crew()
            ###########################################
            # crew_instance.reset_memories(command_type='long')      # Clear long-term memory
            # crew_instance.reset_memories(command_type='entity')    # Clear entity memory
            # crew_instance.reset_memories(command_type='kickoff_outputs')
            crew_instance.reset_memories(command_type='all')
            # crew_instance.reset_memories(command_type='agent_knowledge')
            # crew_instance.reset_memories(command_type='knowledge') # Clear knowledge storage
            ###########################################
            result = crew_instance.kickoff(inputs=inputs)
            print("\n\n########################")
            print("## Crew Execution Finished!")
            print("########################")
            print("\nFinal Result:")
            print(result)

        except Exception as e:
            raise Exception(f"An error occurred while running the crew: {e}")
    else:
        print("\n--- Input is Not Relevant ---")
        print("This crew is specialized for solving problems in computational mechanics and FEM.")
        print("Your request does not appear to be a relevant problem. Please try again.")

if __name__ == "__main__":
    run()


