from typing import List, Optional
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.ollama import Ollama

# 1. Pydantic Schemas for Strict JSON Output
class AtomicFunction(BaseModel):
    name: str = Field(..., description="Name of the function or method")
    description: str = Field(..., description="Detailed description of what this function does")
    parameters: List[str] = Field(default_factory=list, description="List of parameter names and types")
    return_type: str = Field(..., description="Expected return type")

class ProjectClass(BaseModel):
    name: str = Field(..., description="Name of the class")
    description: str = Field(..., description="Purpose of this class")
    methods: List[AtomicFunction] = Field(default_factory=list, description="List of methods belonging to this class")

class ProjectModule(BaseModel):
    name: str = Field(..., description="Filename or module name (e.g., auth_module.py)")
    description: str = Field(..., description="High-level description of this module's responsibility")
    classes: List[ProjectClass] = Field(default_factory=list, description="Classes within this module")
    functions: List[AtomicFunction] = Field(default_factory=list, description="Standalone functions in this module (not in a class)")

class ProjectBreakdown(BaseModel):
    project_name: str = Field(..., description="Name of the overall project")
    summary: str = Field(..., description="Short summary of the breakdown")
    modules: List[ProjectModule] = Field(default_factory=list, description="List of all modules required for the project")

# 2. SLM Agent Definition
# Role: Algorithmic Breakdown
slm_breakdown_agent = Agent(
    name="SLM_Breakdown",
    role="Software Architect Breakdown Specialist",
    model=Ollama(id="qwen2.5:3b"),
    description="You break down complex software requests into atomic, easily implementable parts.",
    instructions=[
        "You are an expert Software Architect.",
        "Your task is to take a user's high-level request and break it down into an algorithmic structure.",
        "CRITICAL: You MUST define at least one Module in the 'modules' list. The 'modules' list MUST NOT be empty.",
        "Inside each Module, you MUST define the necessary Classes and standalone Functions.",
        "Ensure functions are atomic (doing exactly one thing).",
        "If the requested project is very simple (e.g., a simple script, password generator, BMI calculator), DO NOT over-engineer it. Produce only 1 simple module with 1 or 2 functions. Keep the architecture as minimal as possible.",
        "Do NOT write actual source code. Your job is ONLY to produce the architectural blueprint.",
        "Use appropriate design patterns when necessary."
    ],
    output_schema=ProjectBreakdown,
    structured_outputs=True,
    add_history_to_context=False
)
