from fastapi import FastAPI, UploadFile, HTTPException
from api.services.contract_analyzer import ContractAnalyzer
import io

### Create FastAPI instance with custom docs and openapi url
app = FastAPI(docs_url="/api/py/docs", openapi_url="/api/py/openapi.json")
contract_analyzer = ContractAnalyzer()


@app.get("/api/py/helloFastApi")
def hello_fast_api():
    return {"message": "Hello from FastAPI"}


@app.post("/api/py/analyze-contract")
async def analyze_contract(file: UploadFile):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        contents = await file.read()
        result = await contract_analyzer.analyze(contents)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
