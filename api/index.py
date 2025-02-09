from fastapi import FastAPI, UploadFile, HTTPException
from api.services.contract_analyzer import ContractAnalyzer
from api.services.resignation_validator import ResignationValidator
from fastapi.middleware.cors import CORSMiddleware

### Create FastAPI instance with custom docs and openapi url
app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")
contract_analyzer = ContractAnalyzer()
resignation_validator = ResignationValidator()

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000"],  # Next.js 開發服務器
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/hello")
def hello_fast_api():
    return {"message": "Hello from FastAPI"}


@app.post("/api/analyze-contract")
async def analyze_contract(file: UploadFile):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        contents = await file.read()
        result = await contract_analyzer.analyze(contents)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/validate-resignation")
async def validate_resignation(
    file: UploadFile,
    safe_address: str
):
    if not file.filename.endswith(".eml"):
        raise HTTPException(status_code=400, detail="Only .eml files are supported")

    try:
        contents = await file.read()
        result = await resignation_validator.validate_resignation_email(contents, safe_address)
        
        print(result)
        
        if result["is_valid"]:
            return {
                "status": "approved",
                "message": "Resignation request approved",
                "details": result["checks"],
                "safe_address": safe_address,
                "agent_notified": result.get("agent_notified", False)
            }
        else:
            return {
                "status": "rejected",
                "message": "Resignation request rejected",
                "details": result["checks"],
                "safe_address": safe_address
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


