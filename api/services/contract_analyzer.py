from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain.prompts import ChatPromptTemplate
from ..config.settings import settings
from io import BytesIO
import json
import os


class ContractAnalyzer:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key=settings.OPENAI_API_KEY,
        )

        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert in analyzing employment contracts, specifically focusing on resignation clauses and requirements.
            You must analyze the contract and output a structured checklist focusing ONLY on resignation-related details.
            You must output in English.
            IMPORTANT: 
            1. Your response must be a valid JSON object, nothing else.
            2. You must cover ALL the following aspects:
               - Notice period requirements with specific clause references
               - Resignation letter/email format and requirements
               - Submission method and deadlines
               - Who to submit the resignation to (including alternates if specified)
               - Special requirements during notice period
               - Post-resignation obligations with duration
               - Any penalties or consequences for non-compliance
            3. If any aspect is not specified in the contract, provide standard professional recommendations.""",
                ),
                (
                    "user",
                    """Please analyze the following employment contract and provide a resignation checklist in this exact JSON format:
            {{
                "notice_period": {{
                    "duration": "Specify the required notice period",
                    "clause_reference": "Section/Clause number",
                    "exceptions": "Any exceptions to standard notice period"
                }},
                "resignation_letter": {{
                    "required": true/false,
                    "format": "Specify format requirements",
                    "submission_method": "Specify submission methods",
                    "recipient": {{
                        "primary": "Primary recipient",
                        "alternate": "Alternate recipient if any"
                    }},
                    "deadline": "Submission deadline if specified"
                }},
                "special_requirements": [
                    {{
                        "requirement": "Specific requirement",
                        "deadline": "Completion deadline if any",
                        "clause_reference": "Section/Clause number"
                    }}
                ],
                "post_resignation_obligations": [
                    {{
                        "obligation": "Specific obligation",
                        "duration": "Duration of obligation",
                        "clause_reference": "Section/Clause number"
                    }}
                ],
                "compliance_consequences": [
                    "List any penalties or consequences for non-compliance"
                ]
            }}
            
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
            response_text = response.generations[0][0].text.strip()

            # Clean the response text
            response_text = response_text.replace("\n", "")
            response_text = response_text.replace("    ", "")

            # Parse JSON with error handling
            try:
                checklist = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {response_text}")
                raise ValueError(f"Invalid JSON format: {str(e)}")

            # Ensure the response has required fields
            default_structure = {
                "notice_period": {
                    "duration": "Standard notice period (typically 30 days)",
                    "clause_reference": "Not specified in contract",
                    "exceptions": "None specified"
                },
                "resignation_letter": {
                    "required": True,
                    "format": "Written formal letter",
                    "submission_method": "Email and physical copy recommended",
                    "recipient": {
                        "primary": "Immediate supervisor",
                        "alternate": "HR department"
                    },
                    "deadline": "As soon as decision is made"
                },
                "special_requirements": [
                    {
                        "requirement": "Complete handover documentation",
                        "deadline": "Before last working day",
                        "clause_reference": "Standard practice"
                    }
                ],
                "post_resignation_obligations": [
                    {
                        "obligation": "Maintain confidentiality",
                        "duration": "Indefinite",
                        "clause_reference": "Standard practice"
                    }
                ],
                "compliance_consequences": [
                    "Non-compliance may affect future employment references"
                ]
            }

            # Merge the response with default structure
            checklist = {**default_structure, **checklist}

            return {"status": "success", "resignation_checklist": checklist}

        except Exception as e:
            print(f"Full error: {str(e)}")
            print(
                f"Response text: {response_text if 'response_text' in locals() else 'No response'}"
            )
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
