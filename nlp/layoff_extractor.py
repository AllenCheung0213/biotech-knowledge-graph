import os
from pydantic import BaseModel
from langchain import OpenAI, LLMChain, PromptTemplate
from dotenv import load_dotenv

# Load OpenAI key from .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = OpenAI(api_key=OPENAI_API_KEY, temperature=0)

class LayoffSchema(BaseModel):
    num_laid_off: int | None
    percent: float | None

prompt = PromptTemplate(
    input_variables=["description"],
    template="""
Extract from the following layoff description the number of people laid off and the percentage.
If a value is missing, return null.

Description:
\"\"\"
{description}
\"\"\"

Return a JSON object with two keys:
- num_laid_off (integer or null)
- percent (float or null)
"""
)

chain = LLMChain(llm=llm, prompt=prompt)

def extract_layoff(description: str) -> LayoffSchema:
    raw = chain.run(description=description)
    return LayoffSchema.parse_raw(raw)