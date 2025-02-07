from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import PyPDFLoader
from langchain.prompts import ChatPromptTemplate
from ..config.settings import settings
from io import BytesIO
import json
import os


class ContractAnalyzer:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE,
        )

        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert in analyzing employment contracts, specifically focusing on resignation clauses and requirements.
            You must analyze the contract and output a structured checklist focusing ONLY on resignation-related details.
            You must output in Traditional Chinese.
            The output must include information about resignation letter/email requirements if specified in the contract.
            If not explicitly specified, provide standard professional recommendations.""",
                ),
                (
                    "user",
                    """Please analyze the following employment contract and provide a resignation checklist in JSON format.
            The output must include:
            1. Notice period requirements
            2. Resignation letter/email format and requirements
            3. Submission method (email/physical letter/both)
            4. Who to submit the resignation to
            5. Any special requirements during notice period
            6. Any post-resignation obligations
            
            Contract text: {contract_text}""",
                ),
            ]
        )

    async def analyze(self, pdf_content: bytes) -> dict:
        try:
            # Create a temporary file-like object
            pdf_file = BytesIO(pdf_content)

            # Extract text from PDF
            text = self._extract_text_from_pdf(pdf_file)

            # Generate the prompt
            messages = self.prompt_template.format_messages(contract_text=text)

            # Get response from OpenAI
            response = await self.llm.agenerate([messages])

            # Parse the response into JSON
            checklist = json.loads(response.generations[0][0].text)

            # Ensure the response has required fields
            default_structure = {
                "notice_period": "Not specified in contract",
                "resignation_letter": {
                    "required": True,
                    "format": "Written formal letter",
                    "submission_method": "Not specified in contract",
                    "recipient": "Immediate supervisor or HR department",
                },
                "special_requirements": [],
                "post_resignation_obligations": [],
            }

            # Merge the response with default structure
            checklist = {**default_structure, **checklist}

            return {
                "status": "success",
                "resignation_checklist": checklist,
            }
        except Exception as e:
            raise Exception(f"Error analyzing contract: {str(e)}")

    def _extract_text_from_pdf(self, pdf_file) -> str:
        try:
            # Save temporary file
            temp_path = "temp.pdf"
            with open(temp_path, "wb") as f:
                f.write(pdf_file.getvalue())

            # Load and extract text
            loader = PyPDFLoader(temp_path)
            pages = loader.load()

            # Clean up
            os.remove(temp_path)

            # Combine all pages
            text = " ".join([page.page_content for page in pages])
            return text
        except Exception as e:
            raise Exception(f"Error extracting PDF text: {str(e)}")
