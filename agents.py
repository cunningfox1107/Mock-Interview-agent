import os
import json
import requests
from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv
import database as db

def search_internet_questions(query, max_results=5):
    """
    Queries Tavily Search API for relevant ML interview questions/material.
    Returns search results as a concatenated string of content snippets.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        print("Tavily API key not found. Skipping internet search.")
        return ""
    try:
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post("https://api.tavily.com/search", json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            snippets = []
            for r in results:
                snippets.append(f"Source: {r.get('title')} ({r.get('url')})\nContent: {r.get('content')}")
            return "\n\n".join(snippets)
        else:
            print(f"Tavily Search API error: {response.status_code} - {response.text}")
    except Exception as e:
        print("Tavily search failed:", e)
    return ""

# Load environment variables from .env relative to this file
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(base_dir, ".env"))

# Initialize clients if keys exist
def get_openai_client():
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return OpenAI(api_key=key)
    return None

def get_groq_client():
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key)
    return None

def configure_gemini():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        genai.configure(api_key=key)
        return True
    return False

gemini_active = configure_gemini()

def get_active_keys():
    """Returns dict of active APIs."""
    return {
        "OPENAI": bool(os.environ.get("OPENAI_API_KEY")),
        "GEMINI": bool(os.environ.get("GEMINI_API_KEY")),
        "GROQ": bool(os.environ.get("GROQ_API_KEY"))
    }

# ==========================================
# 1. VOICE-TO-TEXT AGENT
# ==========================================
def transcribe_audio(audio_bytes):
    """
    Transcribes audio bytes using Groq Whisper or OpenAI Whisper.
    Fallback to Mock transcript if no keys are found.
    """
    # Try Groq first for speed
    groq_client = get_groq_client()
    if groq_client:
        try:
            # Save bytes to a temp file for the client
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            with open(tmp_path, "rb") as audio_file:
                transcript_obj = groq_client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=audio_file,
                    language="en"
                )
            os.unlink(tmp_path)
            return transcript_obj.text
        except Exception as e:
            print(f"Groq Whisper transcription failed: {e}. Trying OpenAI...")
            
    # Try OpenAI
    openai_client = get_openai_client()
    if openai_client:
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            with open(tmp_path, "rb") as audio_file:
                transcript_obj = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            os.unlink(tmp_path)
            return transcript_obj.text
        except Exception as e:
            print(f"OpenAI Whisper transcription failed: {e}")
            
    # Fallback / Mock
    return "No API keys configured or voice transcription failed. (Please type your answer in the text box below if needed)."

# ==========================================
# HELPER: CHOOSE AND CALL MODEL
# ==========================================
def call_openai(prompt, system_prompt="", model_tier="flash", json_output=False):
    """Utility to call OpenAI API directly."""
    openai_client = get_openai_client()
    if not openai_client:
        print("OpenAI client not configured.")
        return None
    try:
        model_name = "gpt-4o-mini" if model_tier == "flash" else "gpt-4o"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response_format = {"type": "json_object"} if json_output else None
        
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=messages,
            response_format=response_format
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI call failed: {e}")
        return None

def call_llm(prompt, system_prompt="", model_tier="flash", json_output=False):
    """
    Utility to route LLM calls depending on key availability.
    model_tier options: 'flash' (fast/cheap), 'pro' (smart/reasoning)
    """
    # 1. Try Gemini first (preferred for Flash/Pro pricing/context)
    if gemini_active:
        try:
            model_name = "gemini-2.5-flash" if model_tier == "flash" else "gemini-2.5-pro"
            # Using newer models if available
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_prompt if system_prompt else None
                )
            except Exception:
                model = genai.GenerativeModel(model_name="gemini-2.5-flash")
                
            config = {}
            if json_output:
                config["response_mime_type"] = "application/json"
                
            response = model.generate_content(prompt, generation_config=config)
            return response.text
        except Exception as e:
            print(f"Gemini call failed: {e}. Falling back to OpenAI...")
            res = call_openai(prompt, system_prompt, model_tier, json_output)
            if res is not None:
                return res

    # 2. Try Groq (Llama 3.1 70b)
    groq_client = get_groq_client()
    if groq_client:
        try:
            model_name = "llama-3.1-70b-versatile"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response_format = {"type": "json_object"} if json_output else None
            
            response = groq_client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format=response_format
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Groq call failed: {e}. Falling back to OpenAI...")
            res = call_openai(prompt, system_prompt, model_tier, json_output)
            if res is not None:
                return res

    # 3. Otherwise try OpenAI directly if neither of above succeeded or was active
    res = call_openai(prompt, system_prompt, model_tier, json_output)
    if res is not None:
        return res

    # If nothing is configured or all calls failed, return fallback error/mock data
    if json_output:
        return '{"error": "No LLM configuration available or all API keys failed/exhausted."}'
    return "Error: No LLM configuration available or all API keys failed/exhausted."
    return "Mock Response: No LLM configuration available. Please verify API Keys."

def call_llm_openai_first(prompt, system_prompt="", model_tier="flash", json_output=False):
    """
    Utility to route LLM calls trying OpenAI first, and falling back to Gemini if configured, then Groq.
    """
    # 1. Try OpenAI first
    res = call_openai(prompt, system_prompt, model_tier, json_output)
    if res is not None:
        return res

    # 2. Fallback to Gemini
    if gemini_active:
        try:
            model_name = "gemini-2.5-flash" if model_tier == "flash" else "gemini-2.5-pro"
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_prompt if system_prompt else None
                )
            except Exception:
                model = genai.GenerativeModel(model_name="gemini-2.5-flash")
                
            config = {}
            if json_output:
                config["response_mime_type"] = "application/json"
                
            response = model.generate_content(prompt, generation_config=config)
            return response.text
        except Exception as e:
            print(f"Gemini fallback call failed: {e}")

    # 3. Fallback to Groq
    groq_client = get_groq_client()
    if groq_client:
        try:
            model_name = "llama-3.1-70b-versatile"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response_format = {"type": "json_object"} if json_output else None
            
            response = groq_client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format=response_format
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Groq fallback call failed: {e}")

    if json_output:
        return '{"error": "No LLM configuration available or all API keys failed/exhausted."}'
    return "Error: No LLM configuration available or all API keys failed/exhausted."


def chunk_text(text, chunk_size=1500, overlap=300):
    """Chunks text into overlapping segments."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += (chunk_size - overlap)
    return chunks


def retrieve_context_for_topic(pdf_text, topic):
    """
    Retrieves the most keyword-relevant chunks from pdf_text for the given topic.
    """
    chunks = chunk_text(pdf_text)
    if not chunks:
        return ""
    
    # Calculate simple word overlap score
    import re
    topic_words = set(re.findall(r'\w+', topic.lower()))
    if not topic_words:
        return "\n\n".join(chunks[:2])
    
    scored_chunks = []
    for chunk in chunks:
        chunk_words = set(re.findall(r'\w+', chunk.lower()))
        score = len(topic_words.intersection(chunk_words))
        scored_chunks.append((score, chunk))
        
    # Sort by score descending and take top 3
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    best_chunks = [c[1] for c in scored_chunks[:3] if c[0] > 0]
    
    # If no chunk matches topic keywords, fallback to first 2 chunks
    if not best_chunks:
        return "\n\n".join(chunks[:2])
        
    return "\n\n".join(best_chunks)


def run_context_validation_agent(topic, retrieved_content):
    """
    Evaluates if retrieved_content provides enough context for the topic.
    Returns a score between 0.0 and 1.0, and a reasoning explanation.
    Uses Gemini first (via call_llm) and falls back to OpenAI.
    """
    if not retrieved_content or len(retrieved_content.strip()) < 50:
        return 0.0, "Empty or extremely short retrieved content."
        
    system_prompt = (
        "You are an AI Context Validation Agent. Your task is to evaluate if the provided text chunk "
        "contains sufficient, technically deep, and relevant information to generate technical questions "
        "on a specific topic.\n"
        "You MUST return a JSON object with the following keys:\n"
        "- 'score': a float value between 0.0 and 1.0 (where 1.0 is extremely rich/adequate and 0.0 is completely irrelevant or empty)\n"
        "- 'reason': a brief explanation of your evaluation score\n"
        "Do not include markdown block wrappers, just return raw JSON."
    )
    
    prompt = (
        f"Topic to evaluate: '{topic}'\n"
        f"Retrieved Content:\n{retrieved_content}\n\n"
        f"Provide the relevance score and reason."
    )
    
    # Calls call_llm (which tries Gemini first, falls back to OpenAI)
    response_text = call_llm(prompt, system_prompt, model_tier="flash", json_output=True)
    if response_text.startswith("```"):
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
    try:
        data = json.loads(response_text)
        score = float(data.get("score", 0.0))
        reason = data.get("reason", "")
        return score, reason
    except Exception as e:
        print(f"Failed to parse context validation JSON: {e}. Raw response: {response_text}")
        return 0.0, f"Error parsing validation: {str(e)}"


def generate_ai_recommended_answer(question, context_text=None, mode="interview"):
    """
    Generates a recommended answer for a given interview question using a lightweight model.
    Tries OpenAI first (via call_llm_openai_first) and falls back to Gemini.
    If mode is 'resume' and context_text (resume text) is provided, it tailors the answer
    to the candidate's resume achievements and tech stack.
    """
    if mode == "resume" and context_text:
        system_prompt = (
            "You are an AI career coach and expert technical interview assistant. "
            "Your task is to generate a polished, professional, and technically deep recommended answer "
            "for a resume-specific interview question. "
            "You must customize the answer to reflect the candidate's resume achievements, experience, and "
            "technical stack details provided in the resume context."
        )
        prompt = (
            f"Resume Context:\n{context_text[:15000]}\n\n"
            f"Question to answer: {question}\n\n"
            f"Generate a highly professional, strong recommended answer tailored to this resume."
        )
    else:
        system_prompt = (
            "You are an expert Machine Learning Interview Assistant. Your task is to generate a high-quality, "
            "technically sound, and polished recommended answer for a machine learning interview question. "
            "The answer should be structured, concise, and demonstrate deep ML concepts."
        )
        prompt = (
            f"Question: {question}\n\n"
            f"Generate the recommended model answer."
        )
    
    return call_llm_openai_first(prompt, system_prompt, model_tier="flash", json_output=False)


# ==========================================
# 2. QUESTION GENERATOR AGENT
# ==========================================
def generate_interview_questions(user_id, topics, pdf_text, count, easy_cnt, medium_cnt, hard_cnt):
    """
    Generates a set of ML interview questions based on topics or PDF content.
    Returns a list of dicts: [{"id": 1, "question": "...", "difficulty": "...", "topic": "..."}]
    """
    search_context_list = []
    topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    
    for t in topic_list:
        content_found = False
        pdf_retrieved_content = ""
        
        # 1. Try to retrieve and validate context from PDF if pdf_text is present
        if pdf_text:
            pdf_retrieved_content = retrieve_context_for_topic(pdf_text, t)
            score, reason = run_context_validation_agent(t, pdf_retrieved_content)
            print(f"RAG Context Validation for topic '{t}': score={score:.2f}, reason='{reason}'")
            
            if score >= 0.5:
                search_context_list.append(
                    f"Topic: {t}\nSource: Ingested PDF Document Context (validated score: {score:.2f})\nContent:\n{pdf_retrieved_content}"
                )
                content_found = True
            else:
                print(f"PDF context validation score {score:.2f} < 0.5 threshold. Falling back to Tavily search for topic '{t}'...")
                
        # 2. Trigger Tavily search if PDF was not used, or if validation failed, or if no PDF was uploaded
        if not content_found:
            if os.environ.get("TAVILY_API_KEY"):
                query = f"top technical interview questions on {t}"
                res = search_internet_questions(query, max_results=3)
                if res:
                    search_context_list.append(
                        f"Topic: {t}\nSource: Internet Search Fallback (Tavily)\nContent:\n{res}"
                    )
                    content_found = True
            
            if not content_found:
                search_context_list.append(
                    f"Topic: {t}\nSource: Fallback (No Context Available)\nContent: Standard ML knowledge on {t}."
                )

    source_context = "\n\n========================================\n\n".join(search_context_list)

    # Retrieve recently generated questions for repetition control
    past_questions = db.get_recently_generated_questions(limit=200)
    past_exclusion_str = ""
    if past_questions:
        past_exclusion_str = "\n".join([f"- {q}" for q in past_questions])

    # Retrieve user's weak topics for adaptive reinforcement
    weak_topics = db.get_user_weak_topics(user_id, limit=5)
    weak_topics_str = ""
    if weak_topics:
        # Filter weak topics: keep only those sharing a word with the user-specified topics to avoid hallucinations
        import re
        topic_words = set(re.findall(r'\w+', topics.lower()))
        relevant_weak_topics = []
        for wt in weak_topics:
            wt_words = set(re.findall(r'\w+', wt.lower()))
            if wt_words.intersection(topic_words):
                relevant_weak_topics.append(wt)
        
        if relevant_weak_topics:
            weak_topics_str = (
                f"\nAdaptive Reinforcement: The candidate recently scored low on the following relevant sub-topics: {', '.join(relevant_weak_topics)}. "
                f"If and ONLY if any of these sub-topics are relevant to or overlap with the specified interview topics ('{topics}'), you may generate up to 30% of the questions from them. Otherwise, ignore them completely."
            )

    system_prompt = (
        "You are an expert Machine Learning Interviewer. Your task is to generate highly relevant and technical "
        "ML interview questions based on the provided context/topics.\n"
        "CRITICAL INSTRUCTIONS ON TOPIC DISTRIBUTION:\n"
        f"- At least 95% of the generated questions (i.e. at least {max(1, int(count * 0.95))} questions) MUST be strictly and directly about the user-specified topics: '{topics}'.\n"
        "- At most 5% of the questions can be general Machine Learning questions.\n"
        "- Do NOT generate questions on any unrelated topics. For example, do not generate questions on 'AI OCR Business Card Scanner' or specific projects from a candidate's resume/profile, unless those topics are explicitly listed in the user-specified topics.\n"
        "- If you find difficulty in generating the specified questions of the specified level, refer to the Tavily search results provided below to formulate the questions. Do NOT hallucinate questions on unrelated topics.\n"
        f"To ensure maximum diversity and avoid duplication, you MUST NOT generate any questions that are identical or highly similar to these recently used questions:\n{past_exclusion_str}\n"
        f"{weak_topics_str}\n\n"
        "You MUST return a JSON object with a single key 'questions' containing an array of question objects. "
        "Each question object must contain: 'id' (integer), 'question' (string), 'difficulty' (string: 'Easy', 'Medium', or 'Hard'), and 'topic' (string).\n"
        "Generate exactly the requested difficulty counts.\n"
        "Do not include any markdown format blocks like ```json, just return raw JSON text."
    )
    
    prompt = (
        f"Context details:\n{source_context}\n\n"
        f"Total questions requested: {count}\n"
        f"Difficulty distribution: {easy_cnt} Easy, {medium_cnt} Medium, {hard_cnt} Hard.\n"
        f"Generate these questions now."
    )
    
    response_text = call_llm(prompt, system_prompt, model_tier="flash", json_output=True)
    
    # Strip markdown block formatting if model ignores instruction
    if response_text.startswith("```"):
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
    try:
        data = json.loads(response_text)
        questions = data.get("questions", [])
        # Log generated questions to DB for future exclusion
        for q in questions:
            db.log_generated_question(q["question"], "interview")
        return questions
    except Exception as e:
        print(f"Failed to parse questions JSON: {e}. Raw response: {response_text}")
        # Return fallback questions
        return [
            {
                "id": 1, 
                "question": f"Explain the bias-variance trade-off in Machine Learning. (Fallback question, error: {str(e)[:50]})", 
                "difficulty": "Easy", 
                "topic": "Machine Learning Basics"
            }
        ]

# ==========================================
# 3. REVIEWER AGENT (EVALUATOR)
# ==========================================
def run_reviewer_agent(question, user_answer_transcript, difficulty, critique_feedback=""):
    """
    Grades user answer. Returns dict with segment scores.
    """
    system_prompt = (
        "You are a professional AI Scientist and a strict Machine Learning Interviewer. "
        "You must be a bit strict on the interviewee. Analyze each segment of the answer carefully before scoring.\n"
        "Evaluate the user's answer transcript carefully, demanding high rigor, core theoretical depth, and industry standards.\n"
        "You MUST evaluate the answer across three specific segments, scoring each from 0 to 10 (integer):\n"
        "1. 'fluency_score': clarity of communication, flow, vocabulary, and articulation.\n"
        "2. 'professionalism_score': industry professional tone, conciseness, structured layout.\n"
        "3. 'industry_standards_score': technical accuracy, core ML theory correctness, and depth.\n\n"
        "Output a JSON object with the following keys:\n"
        "- 'fluency_score': integer from 0 to 10\n"
        "- 'professionalism_score': integer from 0 to 10\n"
        "- 'industry_standards_score': integer from 0 to 10\n"
        "- 'reasoning': a detailed, critical explanation of why they got these scores, analyzing technical ML details\n"
        "- 'improvements': constructive recommendations on how to improve this answer\n"
        "Do not include any markdown format blocks like ```json, just return raw JSON text."
    )
    
    prompt = (
        f"Question: {question}\n"
        f"Difficulty Level: {difficulty}\n"
        f"User Answer Transcript: {user_answer_transcript}\n"
    )
    
    if critique_feedback:
        prompt += f"\nCRITIQUE FEEDBACK FROM QUALITY CONTROLLER:\n{critique_feedback}\nPlease revise your scoring and analysis incorporating this feedback."

    response_text = call_llm(prompt, system_prompt, model_tier="pro", json_output=True)
    if response_text.startswith("```"):
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
    try:
        eval_data = json.loads(response_text)
        # Parse scores and calculate the average score
        fluency = int(eval_data.get("fluency_score", 5))
        professionalism = int(eval_data.get("professionalism_score", 5))
        standards = int(eval_data.get("industry_standards_score", 5))
        
        avg_score = round((fluency + professionalism + standards) / 3, 2)
        eval_data["score"] = avg_score
        eval_data["fluency_score"] = fluency
        eval_data["professionalism_score"] = professionalism
        eval_data["industry_standards_score"] = standards
        return eval_data
    except Exception as e:
        print(f"Failed to parse Reviewer JSON: {e}")
        return {
            "score": 5.00,
            "fluency_score": 5,
            "professionalism_score": 5,
            "industry_standards_score": 5,
            "reasoning": f"Could not parse evaluation. Transcript received: '{user_answer_transcript}'",
            "improvements": "Ensure your answer is clear and addresses all parts of the question."
        }

# ==========================================
# 4. CRITIQUE AGENT (QUALITY AUDITOR)
# ==========================================
def run_critique_agent(question, user_answer_transcript, evaluation_dict):
    """
    Audits the Reviewer's evaluation.
    Returns dict: {"passed": True/False, "feedback": "..."}
    """
    system_prompt = (
        "You are a Critique Agent / Quality Controller auditing an AI Machine Learning Reviewer. "
        "Verify if the Reviewer's evaluation is accurate, does not contain hallucinated assertions, and "
        "that the score (out of 10) is justified based on the user's transcript.\n"
        "If the Reviewer is overly lenient, overly harsh, or missed key mistakes in the answer, reject it.\n"
        "Output a JSON object with the following keys:\n"
        "- 'passed': boolean (true if the evaluation is accurate and fair, false if it needs adjustment)\n"
        "- 'feedback': detailed feedback explaining why it passed or what needs correction if rejected.\n"
        "Do not write markdown block fences, just return raw JSON."
    )
    
    prompt = (
        f"Question: {question}\n"
        f"User Answer Transcript: {user_answer_transcript}\n"
        f"Reviewer Evaluation:\n{json.dumps(evaluation_dict, indent=2)}\n"
    )
    
    response_text = call_llm(prompt, system_prompt, model_tier="pro", json_output=True)
    if response_text.startswith("```"):
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
    try:
        return json.loads(response_text)
    except Exception as e:
        print(f"Failed to parse Critique JSON: {e}")
        return {"passed": True, "feedback": "Automated pass (critique error)."}

# ==========================================
# ORCHESTRATION: REVIEWER & CRITIQUE LOOP
# ==========================================
def evaluate_answer_with_critique(question, user_answer_transcript, difficulty):
    """
    Runs the Reviewer -> Critique loop. If Critique fails, regenerates the review.
    Limit loop to 2 attempts.
    """
    # Attempt 1
    eval_result = run_reviewer_agent(question, user_answer_transcript, difficulty)
    critique = run_critique_agent(question, user_answer_transcript, eval_result)
    
    if critique.get("passed", True):
        return eval_result
        
    # Attempt 2 (Incorporating critique feedback)
    print(f"Critique rejected evaluation. Feedback: {critique.get('feedback')}")
    revised_eval = run_reviewer_agent(
        question, 
        user_answer_transcript, 
        difficulty, 
        critique_feedback=critique.get("feedback")
    )
    return revised_eval

# ==========================================
# 5. FOLLOW-UP AGENT
# ==========================================
def generate_follow_ups(question, user_answer_transcript, difficulty):
    """
    Generates 3 technical follow-up questions.
    Returns list of 3 strings.
    """
    # Use Llama-3.1-70b (via Groq/OpenAI compatible) for conversational speed
    system_prompt = (
        "You are an expert ML interviewer. Listen to the candidate's answer to the question "
        "and generate exactly three (3) highly specific, technical follow-up questions. "
        "The follow-up questions must probe deeper into the specific explanation the candidate gave, "
        "testing their core understanding at the specified difficulty level.\n"
        "You MUST return a JSON object with a single key 'follow_ups' which is a list of exactly 3 strings.\n"
        "Do not use markdown blocks."
    )
    
    prompt = (
        f"Original Question: {question}\n"
        f"Difficulty: {difficulty}\n"
        f"Candidate's Answer: {user_answer_transcript}\n"
    )
    
    response_text = call_llm(prompt, system_prompt, model_tier="flash", json_output=True)
    if response_text.startswith("```"):
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
    try:
        data = json.loads(response_text)
        return data.get("follow_ups", [])[:3]
    except Exception as e:
        print(f"Failed to parse follow-ups JSON: {e}")
        return [
            "Can you elaborate on your choice of loss function for this scenario?",
            "How would you address overfitting in the model you just described?",
            "What hyperparameters would be most critical to tune here?"
        ]

# ==========================================
# 6. MOCK TEST AGENT
# ==========================================
def generate_mock_test(user_id, topics, pdf_text, num_questions, difficulty="Medium", adaptive_weak_topics=None):
    """
    Generates 15-60 MCQ mock test questions.
    Returns list of dicts: [
      {
         "id": 1, 
         "question": "...", 
         "options": ["A) ..", "B) ..", "C) ..", "D) .."], 
         "correct_option": "A", 
         "explanation": "...",
         "topic": "..."
      }
    ]
    """
    search_context_list = []
    topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    
    for t in topic_list:
        content_found = False
        pdf_retrieved_content = ""
        
        # 1. Try to retrieve and validate context from PDF if pdf_text is present
        if pdf_text:
            pdf_retrieved_content = retrieve_context_for_topic(pdf_text, t)
            score, reason = run_context_validation_agent(t, pdf_retrieved_content)
            print(f"RAG Context Validation for topic '{t}': score={score:.2f}, reason='{reason}'")
            
            if score >= 0.5:
                search_context_list.append(
                    f"Topic: {t}\nSource: Ingested PDF Document Context (validated score: {score:.2f})\nContent:\n{pdf_retrieved_content}"
                )
                content_found = True
            else:
                print(f"PDF context validation score {score:.2f} < 0.5 threshold. Falling back to Tavily search for topic '{t}'...")
                
        # 2. Trigger Tavily search if PDF was not used, or if validation failed, or if no PDF was uploaded
        if not content_found:
            if os.environ.get("TAVILY_API_KEY"):
                portion = max(1, num_questions // len(topic_list))
                query = f"top {difficulty} {portion} questions on {t}"
                res = search_internet_questions(query, max_results=3)
                if res:
                    search_context_list.append(
                        f"Topic: {t}\nSource: Internet Search Fallback (Tavily)\nContent:\n{res}"
                    )
                    content_found = True
            
            if not content_found:
                search_context_list.append(
                    f"Topic: {t}\nSource: Fallback (No Context Available)\nContent: Standard ML knowledge on {t}."
                )

    source_context = "\n\n========================================\n\n".join(search_context_list)

    # Retrieve recently generated questions for repetition control
    past_questions = db.get_recently_generated_questions(limit=200)
    past_exclusion_str = ""
    if past_questions:
        past_exclusion_str = "\n".join([f"- {q}" for q in past_questions])

    # Retrieve user's weak topics for adaptive reinforcement
    weak_topics = db.get_user_weak_topics(user_id, limit=5)
    weak_topics_str = ""
    if weak_topics:
        # Filter weak topics: keep only those sharing a word with the user-specified topics to avoid hallucinations
        import re
        topic_words = set(re.findall(r'\w+', topics.lower()))
        relevant_weak_topics = []
        for wt in weak_topics:
            wt_words = set(re.findall(r'\w+', wt.lower()))
            if wt_words.intersection(topic_words):
                relevant_weak_topics.append(wt)
        
        if relevant_weak_topics:
            weak_topics_str = (
                f"\nAdaptive Reinforcement: The candidate recently struggled with these relevant sub-topics: {', '.join(relevant_weak_topics)}. "
                f"If and ONLY if any of these sub-topics are relevant to or overlap with the specified test topics ('{topics}'), you may generate up to 30% of the questions from them. Otherwise, ignore them completely."
            )

    # Include the direct adaptive weak topics from the current attempt if provided
    if adaptive_weak_topics:
        weak_topics_str += (
            f"\nADAPTIVE FOCUS: This is an adaptive test following a previous attempt. The candidate recently answered questions on "
            f"these specific sub-topics incorrectly: {', '.join(adaptive_weak_topics)}. "
            f"You MUST increase the weightage of these specific sub-topics, generating between 60% and 80% of the questions from them, "
            f"while still ensuring all questions remain within the overall specified topics: '{topics}'."
        )

    system_prompt = (
        "You are a Mock Test Agent. Your task is to generate a comprehensive machine learning multiple-choice test. "
        f"Generate exactly {num_questions} questions at a strict '{difficulty}' difficulty level.\n"
        "CRITICAL INSTRUCTIONS ON TOPIC DISTRIBUTION:\n"
        f"- At least 95% of the generated questions (i.e. at least {max(1, int(num_questions * 0.95))} questions) MUST be strictly and directly about the user-specified topics: '{topics}'.\n"
        "- At most 5% of the questions can be general Machine Learning questions.\n"
        "- Do NOT generate questions on any unrelated topics. For example, do not generate questions on 'AI OCR Business Card Scanner' or specific projects from a candidate's resume/profile, unless those topics are explicitly listed in the user-specified topics.\n"
        "- If you find difficulty in generating the specified questions of the specified level, refer to the Tavily search results provided below to formulate the questions. Do NOT hallucinate questions on unrelated topics.\n"
        f"To ensure maximum diversity and avoid duplication, you MUST NOT generate any MCQ questions that are identical or highly similar to these recently used questions:\n{past_exclusion_str}\n"
        f"{weak_topics_str}\n\n"
        "You MUST return a JSON object with a single key 'test_questions' containing an array of question objects. "
        "Each object must contain:\n"
        "- 'id': integer\n"
        "- 'question': string\n"
        "- 'options': list of exactly 4 strings (formatted as 'A) ...', 'B) ...', etc.)\n"
        "- 'correct_option': string (either 'A', 'B', 'C', or 'D')\n"
        "- 'explanation': a brief text explaining the correct answer\n"
        "- 'topic': string (the specific sub-topic this question belongs to, e.g. 'Regularization', 'Gradient Descent', 'SVM')\n"
        "Ensure questions test a range of concepts at the specified difficulty. Do not include markdown wrappers."
    )
    
    prompt = (
        f"Context details:\n{source_context}\n\n"
        f"Number of questions to generate: {num_questions}\n"
    )
    
    response_text = call_llm(prompt, system_prompt, model_tier="flash", json_output=True)
    if response_text.startswith("```"):
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
    try:
        data = json.loads(response_text)
        test_qs = data.get("test_questions", [])
        # Log generated test questions to DB for future exclusion
        for q in test_qs:
            db.log_generated_question(q["question"], "test")
        return test_qs
    except Exception as e:
        print(f"Failed to parse mock test JSON: {e}")
        # Generate basic fallback questions
        return [
            {
                "id": 1,
                "question": "Which of the following algorithms is an ensemble learning method?",
                "options": ["A) Linear Regression", "B) Random Forest", "C) Support Vector Machine", "D) K-Means Clustering"],
                "correct_option": "B",
                "explanation": "Random Forest is an ensemble method consisting of multiple decision trees.",
                "topic": "Ensemble Methods"
            }
        ]

def generate_synthesis_report(interview_qas):
    """
    Generates a professional synthesis report from a strict AI Scientist's perspective.
    """
    qa_summary_list = []
    for idx, qa in enumerate(interview_qas):
        # Determine if it's follow up
        q_type = "Follow-up" if qa.get('is_follow_up') else "Core Question"
        qa_summary_list.append(
            f"[{q_type} {idx+1}] Question: {qa['question']}\n"
            f"Candidate Answer: {qa['user_answer_transcript']}\n"
            f"Reviewer Ratings:\n"
            f" - Fluency: {qa.get('fluency_score', 0)}/10\n"
            f" - Professionalism: {qa.get('professionalism_score', 0)}/10\n"
            f" - Industry Standards / Depth: {qa.get('industry_standards_score', 0)}/10\n"
            f" - Overall Score: {qa.get('reviewer_score', 0)}/10\n"
            f"Reviewer Feedback: {qa.get('reviewer_reasoning')}\n"
            f"----------------------------------------"
        )
    
    interview_transcript = "\n".join(qa_summary_list)
    
    system_prompt = (
        "You are a Principal AI Research Scientist and strict Machine Learning Interviewer. "
        "Your task is to write a highly professional, rigorous synthesis report on the candidate's performance.\n"
        "Be extremely honest, critical, and a bit hard on the candidate. Evaluate if their answers meet true "
        "industry and academic standards for senior machine learning positions.\n"
        "Structure your report into the following sections using clear Markdown formatting:\n"
        "1. Executive Summary & Hiring Recommendation (e.g. Strongly Hire, Lean Hire, No Hire - with firm justification)\n"
        "2. Technical Depth & Domain Expertise Analysis (e.g., MLOps, deep learning theory, feature engineering)\n"
        "3. Core Strengths Identified (bullet points)\n"
        "4. Critical Gaps & Areas of Improvement (bullet points)\n"
        "5. Fluency & Professionalism Assessment"
    )
    
    prompt = (
        f"Here is the complete interview transcript, scores, and individual question evaluations:\n\n"
        f"{interview_transcript}\n\n"
        f"Generate the comprehensive synthesis report now."
    )
    
    return call_llm(prompt, system_prompt, model_tier="pro", json_output=False)


# ==========================================
# 7. WEAKNESS ANALYZER AGENT
# ==========================================
def generate_test_weakness_analysis(wrong_questions_details):
    """
    Generates a highly professional technical study guide and analysis of incorrect answers.
    Persona: Principal AI Research Scientist.
    """
    if not wrong_questions_details:
        return "### 📊 Weakness Analysis\nCongratulations! You answered all questions correctly. No weaknesses identified."
        
    wrong_summary = []
    for idx, q in enumerate(wrong_questions_details):
        wrong_summary.append(
            f"Question {idx+1}: {q['question']}\n"
            f"Topic/Sub-topic: {q.get('topic', 'General ML')}\n"
            f"Your Choice: {q['user_choice']} | Correct Choice: {q['correct_choice']}\n"
            f"Explanation: {q['explanation']}\n"
            f"----------------------------------------"
        )
    wrong_text = "\n".join(wrong_summary)
    
    system_prompt = (
        "You are a Principal AI Scientist and Senior ML Educator. "
        "Your task is to analyze the candidate's incorrect answers on their multiple-choice exam "
        "and write a highly structured, critical, and constructive weakness analysis and study plan.\n"
        "Be professional, rigorous, and tell them exactly which theoretical principles or MLOps practices "
        "they are failing to grasp.\n"
        "Structure your response using Markdown:\n"
        "### 📊 Key Concept Weaknesses Identified\n"
        "Identify 2-3 main conceptual gaps based on their mistakes.\n"
        "### 📚 Custom Study Recommendations\n"
        "Provide concrete suggestions on what they should study next, citing specific techniques or architectures."
    )
    
    prompt = (
        f"Here are the details of the questions the candidate answered incorrectly:\n\n"
        f"{wrong_text}\n\n"
        f"Generate the weakness analysis and custom study guide now."
    )
    
    return call_llm(prompt, system_prompt, model_tier="pro", json_output=False)


# ==========================================
# 8. RESUME AGENT
# ==========================================
def generate_resume_questions(resume_text, num_questions, difficulty, candidate_name):
    """
    Generates a list of questions for a Resume Round technical interview.
    Returns a list of dicts: [{"id": 1, "question": "...", "difficulty": "...", "topic": "..."}]
    """
    system_prompt = (
        "You are an expert technical interviewer and Principal AI Scientist. "
        f"You are designing questions for a Resume Round interview for the candidate: {candidate_name}.\n"
        "You MUST return a JSON object with a key 'questions' containing an array of question objects.\n"
        "The first question (id: 1) MUST always be a general introduction question: 'Please introduce yourself and walk me through your background and key machine learning experiences.'\n"
        f"Subsequent questions must be highly technical questions probing the specific projects, architectures, algorithms, and technical work mentioned in their resume. Match the overall difficulty level '{difficulty}'.\n"
        "Each question object must contain: 'id' (integer), 'question' (string), 'difficulty' (string), and 'topic' (string: specific tech topic from resume, e.g. 'Transformer Attention', 'OCR Pipeline').\n"
        f"Ensure all generated questions and topics are framed for candidate '{candidate_name}' and there is no name mismatch. Do NOT refer to any other name in your output.\n"
        "Do not include markdown wrappers."
    )
    
    prompt = (
        f"Candidate Name: {candidate_name}\n"
        f"Parsed Resume Text:\n{resume_text[:20000]}\n\n"
        f"Total questions to generate (including the introduction): {num_questions}\n"
        f"Difficulty: {difficulty}\n"
        f"Generate these questions now."
    )
    
    response_text = call_llm(prompt, system_prompt, model_tier="pro", json_output=True)
    if response_text.startswith("```"):
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
    try:
        data = json.loads(response_text)
        questions = data.get("questions", [])
        # Log them
        for q in questions:
            db.log_generated_question(q["question"], "resume")
        return questions
    except Exception as e:
        print("Error parsing resume questions:", e)
        # Fallback
        return [
            {"id": 1, "question": "Please introduce yourself and walk me through your background and key machine learning experiences.", "difficulty": difficulty, "topic": "Introduction"},
            {"id": 2, "question": "Can you describe the most challenging ML project listed on your resume and how you evaluated its performance?", "difficulty": difficulty, "topic": "Project Details"},
            {"id": 3, "question": "What tools and libraries did you use to build the data pipelines for your projects, and how did you handle data quality?", "difficulty": difficulty, "topic": "Data Pipelines"}
        ]

def run_resume_reviewer_agent(question, user_answer_transcript, difficulty, candidate_name, critique_feedback=""):
    """
    Evaluates resume round answers. Scores Fluency, Technical Depth, and Professionalism out of 10.
    """
    system_prompt = (
        "You are a strict, senior Data Scientist and professional Communication Specialist. "
        f"Your job is to critically evaluate the candidate's ({candidate_name}) response to a resume-specific question.\n"
        "Be rigorous, technical, and do not be easy on them. Evaluate if their answers show genuine depth and communication skills.\n"
        f"Refer to the candidate as {candidate_name} in your reasoning. Do NOT use or guess any other name from the resume.\n"
        "You MUST evaluate the answer across three specific segments, scoring each from 0 to 10 (integer):\n"
        "1. 'fluency_score': clarity of presentation, communication skill, flow, and expression.\n"
        "2. 'professionalism_score': industry professional delivery, conciseness, structured overview.\n"
        "3. 'technical_depth_score': technical depth, correctness of ML details, project architecture knowledge.\n\n"
        "Output a JSON object with the following keys:\n"
        "- 'fluency_score': integer from 0 to 10\n"
        "- 'professionalism_score': integer from 0 to 10\n"
        "- 'technical_depth_score': integer from 0 to 10\n"
        "- 'reasoning': a detailed, critical explanation of why they got these scores\n"
        "- 'improvements': constructive recommendations on how to improve this answer\n"
        "Do not include any markdown format blocks like ```json, just return raw JSON text."
    )
    
    prompt = (
        f"Candidate Name: {candidate_name}\n"
        f"Question asked: {question}\n"
        f"Difficulty Level: {difficulty}\n"
        f"Candidate Answer: {user_answer_transcript}\n"
    )
    
    if critique_feedback:
        prompt += f"\nCritique Feedback: {critique_feedback}\nPlease revise your scoring."
        
    response_text = call_llm(prompt, system_prompt, model_tier="pro", json_output=True)
    if response_text.startswith("```"):
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
    try:
        eval_data = json.loads(response_text)
        fluency = int(eval_data.get("fluency_score", 5))
        professionalism = int(eval_data.get("professionalism_score", 5))
        depth = int(eval_data.get("technical_depth_score", 5))
        
        avg_score = round((fluency + professionalism + depth) / 3, 2)
        eval_data["score"] = avg_score
        eval_data["fluency_score"] = fluency
        eval_data["professionalism_score"] = professionalism
        eval_data["industry_standards_score"] = depth # Map to industry standards column in DB
        return eval_data
    except Exception as e:
        print("Error parsing resume review:", e)
        return {
            "score": 5.0,
            "fluency_score": 5,
            "professionalism_score": 5,
            "industry_standards_score": 5,
            "reasoning": f"Could not parse evaluation. Transcript received: '{user_answer_transcript}'",
            "improvements": "Make sure your answer is technically thorough."
        }

def evaluate_resume_answer_with_critique(question, user_answer_transcript, difficulty, candidate_name):
    """Runs the Resume Reviewer -> Critique loop."""
    eval_result = run_resume_reviewer_agent(question, user_answer_transcript, difficulty, candidate_name)
    critique = run_critique_agent(question, user_answer_transcript, eval_result)
    if critique.get("passed", True):
        return eval_result
    
    revised_eval = run_resume_reviewer_agent(
        question, 
        user_answer_transcript, 
        difficulty, 
        candidate_name,
        critique_feedback=critique.get("feedback")
    )
    return revised_eval

def generate_resume_synthesis_report(interview_qas, candidate_name):
    """Generates a strict Data Scientist evaluation report of the Resume Round."""
    qa_summary_list = []
    for idx, qa in enumerate(interview_qas):
        qa_summary_list.append(
            f"[Question {idx+1}] Question: {qa['question']}\n"
            f"Candidate Answer: {qa['user_answer_transcript']}\n"
            f"Reviewer Ratings:\n"
            f" - Fluency: {qa.get('fluency_score', 0)}/10\n"
            f" - Professionalism: {qa.get('professionalism_score', 0)}/10\n"
            f" - Technical Depth: {qa.get('industry_standards_score', 0)}/10\n"
            f" - Overall Score: {qa.get('reviewer_score', 0)}/10\n"
            f"Reviewer Feedback: {qa.get('reviewer_reasoning')}\n"
            f"----------------------------------------"
        )
    interview_transcript = "\n".join(qa_summary_list)
    
    system_prompt = (
        "You are a strict, senior Data Scientist and professional Communication Specialist conducting a resume evaluation.\n"
        f"Your task is to write a highly professional, rigorous synthesis report on the candidate's ({candidate_name}) performance. "
        "Be extremely honest, critical, and a bit hard on the candidate. Evaluate if their answers meet true "
        "technical depth and professional communication standards (not easy-going, but tough and to par).\n"
        f"You must refer to the candidate as {candidate_name} throughout the report. Do NOT use or guess any other name from the resume.\n"
        "Structure your report into the following sections using Markdown formatting:\n"
        "1. Resume Authenticity & Depth Verdict (e.g. Strong Match, Partial Match, Lack of Depth - with firm justification)\n"
        "2. Technical Project Architecture Analysis (evaluating their understanding of projects listed on their resume)\n"
        "3. Communication & Fluency Assessment\n"
        "4. Critical Gaps & Areas of Improvement"
    )
    
    prompt = (
        f"Here is the complete resume round interview transcript, scores, and evaluations:\n\n"
        f"{interview_transcript}\n\n"
        f"Generate the comprehensive resume round synthesis report now."
    )
    return call_llm(prompt, system_prompt, model_tier="pro", json_output=False)
