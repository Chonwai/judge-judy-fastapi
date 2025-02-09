from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from datetime import datetime
import email.utils
from email import message_from_bytes
from ..config.settings import settings
import json
import httpx


class ResignationValidator:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key=settings.OPENAI_API_KEY,
            model_kwargs={"response_format": {"type": "json_object"}},
        )

        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert in analyzing resignation emails.
                You must analyze the email content and extract key resignation information.
                You must output in English.
                IMPORTANT:
                1. Your response must be a valid JSON object, nothing else.
                2. You must extract ALL the following aspects:
                   - Last working day (in YYYY-MM-DD format)
                   - Notice period calculation (from email sent date)
                   - Email format validation
                   - Recipient validation
                   - Any special conditions or requests
                3. Current date for reference: {current_date}
                4. Email sent date for reference: {sent_date}
                
                Output format:
                {{
                    "last_working_day": "YYYY-MM-DD",
                    "notice_period_days": number,
                    "format_check": {{
                        "is_valid": boolean,
                        "details": "Explanation"
                    }},
                    "special_notes": [
                        "List any special conditions or requests"
                    ]
                }}
                
                Validation rules:
                1. Format check: Must include resignation statement, last working day, and professional tone
                2. Notice period: Calculate days between sent_date and last_working_day""",
                ),
                (
                    "user",
                    "Please analyze the following resignation email:\n\nFrom: {sender}\nTo: {recipients}\nSubject: {subject}\nDate: {sent_date}\n\nBody:\n{body}",
                ),
            ]
        )

    async def _notify_agent(self, safe_address: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://judgejudyagent.vercel.app/api/agent",
                    json={"safeAddress": safe_address},
                    headers={"Content-Type": "application/json"}
                )
                
                print("response: ", response.json())
                
                if response.status_code != 200:
                    print(f"Agent API error: {response.status_code}")
                    return False
                
                result = response.json()
                print("result: ", result)
                return result.get("success", False)
        except Exception as e:
            print(f"Error notifying agent: {str(e)}")
            return False

    async def validate_resignation_email(self, eml_content: bytes, safe_address: str = None) -> dict:
        try:
            # Parse email content
            email_message = message_from_bytes(eml_content)

            # Extract email components
            email_data = self._extract_email_data(email_message)

            # Generate the prompt
            current_date = datetime.now().strftime("%Y-%m-%d")
            messages = self.prompt_template.format_messages(
                current_date=current_date, **email_data
            )

            # Get response from OpenAI
            response = self.llm.invoke(messages)
            analysis = json.loads(response.content)

            print("analysis: ", analysis)

            # Process the analysis
            validation_results = {
                "is_valid": True,
                "checks": {
                    "notice_period": {
                        "passed": int(analysis["notice_period_days"]) >= 30,
                        "details": f"Given {analysis['notice_period_days']} days notice",
                        "required_days": 30,
                    },
                    "format": analysis["format_check"],
                    "special_notes": analysis["special_notes"],
                },
            }

            print(validation_results)

            # Overall validation
            validation_results["is_valid"] = all(
                [
                    validation_results["checks"]["notice_period"]["passed"],
                    validation_results["checks"]["format"]["is_valid"],
                ]
            )

            # 如果驗證通過且提供了 safe_address，則通知 agent
            if validation_results["is_valid"] and safe_address:
                agent_notified = await self._notify_agent(safe_address)
                print("agent_notified: ", agent_notified)
                validation_results["agent_notified"] = agent_notified

            return validation_results

        except Exception as e:
            raise Exception(f"Error validating resignation email: {str(e)}")

    def _extract_email_data(self, email_message) -> dict:
        # Get email body
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = email_message.get_payload(decode=True).decode()

        # Extract other components
        sent_date = email_message.get("Date", "")
        if sent_date:
            sent_date = datetime.fromtimestamp(
                email.utils.mktime_tz(email.utils.parsedate_tz(sent_date))
            ).strftime("%Y-%m-%d")

        return {
            "sender": email_message.get("From", ""),
            "recipients": email_message.get("To", ""),
            "subject": email_message.get("Subject", ""),
            "sent_date": sent_date,
            "body": body,
        }
