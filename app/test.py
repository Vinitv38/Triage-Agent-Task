from groq import Groq

from models import TriageResult
from prompts import TRIAGE_AGENT_PROMPT
from config import GROQ_API_KEY, GROQ_MODEL
import json


client = Groq(api_key=GROQ_API_KEY)
gen_res = client.chat.completions.create(
    model="moonshotai/kimi-k2-instruct-0905",
    messages=[{"role": "user", "content": TRIAGE_AGENT_PROMPT}],
    temperature=0.0,
    max_tokens=400,
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "Triage_Result",
            "schema": TriageResult.schema()
        }
    }, 
)
resp = TriageResult.model_validate(json.loads(gen_res.choices[0].message.content))
resp= resp.model_dump()
print(resp)