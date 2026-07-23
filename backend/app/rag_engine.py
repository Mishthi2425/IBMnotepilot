import os
import re
import time
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np


class RAGEngine:
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.persist_dir = persist_dir
        self._load_env()
        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        print("Embedding model loaded!")
        self.chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        print("ChromaDB initialized!")

    def _load_env(self):
        from dotenv import load_dotenv
        for env_path in [
            os.path.join(os.getcwd(), '.env'),
            os.path.join(os.path.dirname(__file__), '..', '.env'),
        ]:
            if os.path.exists(env_path):
                load_dotenv(env_path, override=True)
                break
        self.llm_api_key = os.getenv("LLM_API_KEY", "").strip()
        self.llm_base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.llm_model = os.getenv("LLM_MODEL", "openai/gpt-3.5-turbo")
        print(f"LLM: {'ON' if self.llm_api_key else 'OFF'} | {self.llm_model} | {self.llm_base_url}")

    def get_embedding(self, text: str) -> List[float]:
        return self.embedding_model.encode(text).tolist()

    def _clean_ocr_text(self, text: str) -> str:
        text = re.sub(r'(\w)\s+(\w)', r'\1\2', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def create_vector_store(self, document_id: str, chunks: List[str]):
        collection_name = f"doc_{document_id}"
        try:
            self.chroma_client.delete_collection(collection_name)
        except:
            pass
        collection = self.chroma_client.create_collection(collection_name)
        for i, chunk in enumerate(chunks):
            collection.add(
                ids=[f"chunk_{i}"],
                embeddings=[self.get_embedding(chunk)],
                documents=[chunk],
                metadatas=[{"chunk_id": i}]
            )
        print(f"Vector store created with {len(chunks)} chunks!")

    def _web_search(self, query: str) -> Optional[str]:
        try:
            from ddgs import DDGS
            results = DDGS().text(query, max_results=5)
            if results:
                snippets = []
                for r in results:
                    body = r.get("body", "")
                    if body:
                        snippets.append(body)
                return "\n\n".join(snippets) if snippets else None
            return None
        except Exception as e:
            print(f"Web search error: {e}")
            return None

    def _is_google_api(self) -> bool:
        return "generativelanguage.googleapis.com" in self.llm_base_url

    def _call_llm(self, prompt: str, max_tokens: int = 2000, retries: int = 5) -> Optional[str]:
        if not self.llm_api_key:
            print("No LLM key")
            return None
        import requests
        headers = {"Authorization": f"Bearer {self.llm_api_key}", "Content-Type": "application/json"}

        for attempt in range(retries):
            try:
                if self._is_google_api():
                    url = f"{self.llm_base_url}/models/{self.llm_model}:generateContent?key={self.llm_api_key}"
                    payload = {
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "systemInstruction": {"parts": [{"text": "You are an expert academic tutor. Give clear, accurate, well-structured answers. Do NOT use LaTeX, math symbols, or special notation like \\frac, \\sum, \\hat, \\partial. Write math in plain English instead."}]},
                        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3}
                    }
                    resp = requests.post(url, json=payload, timeout=90)
                else:
                    url = f"{self.llm_base_url}/chat/completions"
                    payload = {
                        "model": self.llm_model,
                        "messages": [{"role": "system", "content": "You are an expert academic tutor. Give clear, accurate, well-structured answers. Do NOT use LaTeX, math symbols, or special notation like \\frac, \\sum, \\hat, \\partial. Write math in plain English instead."}, {"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": 0.3
                    }
                    resp = requests.post(url, headers=headers, json=payload, timeout=90)

                print(f"LLM attempt {attempt+1}: {resp.status_code}")
                if resp.status_code == 200:
                    if self._is_google_api():
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "").strip()
                        return None
                    else:
                        return resp.json()["choices"][0]["message"]["content"].strip()

                if resp.status_code == 429:
                    wait = min(2 ** (attempt + 1), 30)
                    print(f"Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code >= 500:
                    time.sleep(3)
                    continue
                print(f"LLM error {resp.status_code}: {resp.text[:200]}")
                return None
            except requests.exceptions.Timeout:
                print(f"LLM timeout on attempt {attempt+1}")
                time.sleep(2)
            except Exception as e:
                print(f"LLM exception: {e}")
                return None
        print("LLM: all retries failed")
        return None

    def _call_llm_stream(self, prompt: str, max_tokens: int = 2000, retries: int = 5):
        if not self.llm_api_key:
            yield "No LLM API key configured."
            return
        import requests
        headers = {"Authorization": f"Bearer {self.llm_api_key}", "Content-Type": "application/json"}

        for attempt in range(retries):
            try:
                if self._is_google_api():
                    url = f"{self.llm_base_url}/models/{self.llm_model}:streamGenerateContent?key={self.llm_api_key}"
                    payload = {
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "systemInstruction": {"parts": [{"text": "You are an expert academic tutor. Give clear, accurate, well-structured answers. Do NOT use LaTeX, math symbols, or special notation like \\frac, \\sum, \\hat, \\partial. Write math in plain English instead."}]},
                        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3}
                    }
                    resp = requests.post(url, json=payload, timeout=90, stream=True)
                    print(f"LLM stream attempt {attempt+1}: {resp.status_code}")
                    if resp.status_code == 200:
                        for line in resp.iter_lines():
                            if line:
                                line = line.decode("utf-8")
                                if line.startswith("{"):
                                    try:
                                        import json
                                        data = json.loads(line)
                                        candidates = data.get("candidates", [])
                                        if candidates:
                                            parts = candidates[0].get("content", {}).get("parts", [])
                                            for part in parts:
                                                text = part.get("text", "")
                                                if text:
                                                    yield text
                                    except:
                                        pass
                        return
                else:
                    url = f"{self.llm_base_url}/chat/completions"
                    payload = {
                        "model": self.llm_model,
                        "messages": [{"role": "system", "content": "You are an expert academic tutor. Give clear, accurate, well-structured answers. Do NOT use LaTeX, math symbols, or special notation like \\frac, \\sum, \\hat, \\partial. Write math in plain English instead."}, {"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": 0.3,
                        "stream": True
                    }
                    resp = requests.post(url, headers=headers, json=payload, timeout=90, stream=True)
                    print(f"LLM stream attempt {attempt+1}: {resp.status_code}")
                    if resp.status_code == 200:
                        for line in resp.iter_lines():
                            if line:
                                line = line.decode("utf-8")
                                if line.startswith("data: ") and line != "data: [DONE]":
                                    try:
                                        import json
                                        chunk = json.loads(line[6:])
                                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                        if delta:
                                            yield delta
                                    except:
                                        pass
                        return

                if resp.status_code == 429:
                    wait = min(2 ** (attempt + 1), 30)
                    print(f"Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code >= 500:
                    time.sleep(3)
                    continue
                print(f"LLM stream error {resp.status_code}")
                return
            except requests.exceptions.Timeout:
                print(f"LLM stream timeout on attempt {attempt+1}")
                time.sleep(2)
            except Exception as e:
                print(f"LLM stream exception: {e}")
                time.sleep(1)
        print("LLM stream: all retries failed")

    def _tokenize(self, text: str) -> List[str]:
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'shall', 'can', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
            'before', 'after', 'and', 'but', 'or', 'not', 'no', 'so', 'yet',
            'than', 'too', 'very', 'just', 'about', 'also', 'how', 'what', 'when',
            'where', 'who', 'which', 'whom', 'why', 'this', 'that', 'these', 'those',
            'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his',
            'she', 'her', 'it', 'its', 'they', 'them', 'their'
        }
        return [w for w in re.findall(r'\w+', text.lower()) if w not in stop_words and len(w) > 2]

    def _check_relevance(self, query: str, context: str) -> bool:
        clean_query = re.sub(r'[?!.,;:]', '', query).strip().lower()
        clean_context = context.lower()

        qt = set(self._tokenize(clean_query))
        ct = set(self._tokenize(clean_context))
        if not qt:
            return True

        abbrev_map = {'ai': ['artificial', 'intelligence'], 'ml': ['machine', 'learning'],
                      'dl': ['deep', 'learning'], 'nn': ['neural', 'network'],
                      'cv': ['computer', 'vision'], 'nlp': ['natural', 'language', 'processing']}
        for abbr, full_words in abbrev_map.items():
            if abbr in qt:
                if all(w in clean_context for w in full_words):
                    return True

        # Use embedding similarity for semantic matching
        try:
            import numpy as np
            q_emb = np.array(self.get_embedding(clean_query))
            c_emb = np.array(self.get_embedding(clean_context[:1000]))
            sim = float(np.dot(q_emb, c_emb) / (np.linalg.norm(q_emb) * np.linalg.norm(c_emb)))
            print(f"Relevance similarity: {sim:.3f}")
            if sim > 0.5:
                return True
        except Exception as e:
            print(f"Embedding similarity error: {e}")

        direct = len(qt & ct) / len(qt) if qt else 0
        return direct >= 0.3

    def query(self, document_id: str, query: str, explanation_level: str = "detailed",
              conversation_history: List[Dict] = None) -> Dict[str, Any]:

        self._load_env()

        # Detect follow-up questions and resolve the actual topic
        followup_words = {'longer', 'shorter', 'more', 'less', 'explain', 'elaborate',
                          'detail', 'summarize', 'again', 'simpler', 'easier', 'harder',
                          'better', 'differently', 'expand', 'continue', 'more detail',
                          'tell me more', 'go on', 'what else'}
        followup_phrases = ['did not understand', "didn't understand", 'didnt understand',
                            'not understand', 'confused', 'unclear', 'can you explain',
                            'what does that mean', 'what do you mean', 'say that again',
                            'repeat', 'simpler', 'easier', 'in simple terms', 'like im 5',
                            "like i'm 5", 'eli5', 'break it down', 'step by step',
                            'over my head', 'too complicated', 'too complex', 'too hard',
                            'too difficult', 'make it simple', 'dumb it down', 'plain english',
                            'i dont get', "i don't get", 'i dont understand', "i don't understand",
                            'not clear', 'bit confused', 'little confused', 'doesnt make sense',
                            "doesn't make sense", 'went over my head', 'went above my head']
        actual_query = query
        clean_q = re.sub(r'[?!.,;:]', '', query).strip().lower()

        is_followup = (clean_q in followup_words or len(clean_q.split()) <= 2 or
                       any(phrase in clean_q for phrase in followup_phrases))

        if is_followup and conversation_history:
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    prev = msg.get("content", "").strip()
                    if prev and prev.lower() != clean_q:
                        actual_query = prev + " " + query
                        print(f"Follow-up detected. Expanded query: '{actual_query}'")
                        break

        # Expand abbreviations for relevance checking too
        expand_map = {'ai': 'artificial intelligence', 'ml': 'machine learning',
                      'dl': 'deep learning', 'nn': 'neural network',
                      'cv': 'computer vision', 'nlp': 'natural language processing'}
        relevance_query = actual_query
        clean_aq = re.sub(r'[?!.,;:]', '', actual_query).strip().lower()
        for abbr, full in expand_map.items():
            if abbr == clean_aq or abbr + '?' == clean_aq or abbr + '/' == clean_aq:
                relevance_query = full
                print(f"Expanded relevance query: '{relevance_query}'")
                break
            # Check if abbreviation appears as a word in the query
            if re.search(r'\b' + abbr + r'\b', clean_aq):
                relevance_query = re.sub(r'\b' + abbr + r'\b', full, clean_aq)
                print(f"Expanded relevance query: '{relevance_query}'")
                break

        # Get document context
        combined_context = ""
        sources = []
        try:
            collection = self.chroma_client.get_collection(f"doc_{document_id}")
            results = collection.query(query_embeddings=[self.get_embedding(query)], n_results=10)
            if results['documents'] and results['documents'][0]:
                all_chunks = results['documents'][0]
                combined_context = "\n\n".join(all_chunks)
                sources = [{"content": doc[:500], "metadata": {}, "type": "document"} for doc in all_chunks]
        except Exception as e:
            print(f"Collection error: {e}")

        # Build history text
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-6:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_text += f"{role}: {msg.get('content', '')}\n"
        history_section = f"Conversation History:\n{history_text}\n" if history_text else ""

        # Token limits per level
        max_tok = {"basic": 800, "comprehensive": 4000}.get(explanation_level, 3000)

        # Check relevance before calling LLM
        doc_relevant = False
        if combined_context:
            doc_relevant = self._check_relevance(relevance_query, combined_context)
            print(f"Doc relevant for '{relevance_query}': {doc_relevant}")

        # If document is relevant, try LLM
        if doc_relevant and combined_context:
            print(f"Document has answer, rephrasing via LLM for: {actual_query}")

            # Clean, deduplicate, and score chunks by relevance
            seen = set()
            clean_chunks = []
            for chunk in all_chunks:
                fixed = self._clean_ocr_text(chunk)
                if fixed not in seen and len(fixed) > 30:
                    seen.add(fixed)
                    clean_chunks.append(fixed)

            query_words = set(self._tokenize(relevance_query))
            scored = []
            for c in clean_chunks:
                chunk_words = set(self._tokenize(c))
                overlap = len(query_words & chunk_words)
                scored.append((overlap, c))
            scored.sort(key=lambda x: -x[0])
            top_chunks = [c for _, c in scored[:4]]
            context_for_llm = "\n\n".join(top_chunks)

            length_inst = {
                "basic": "Give a concise 2-3 sentence summary.",
                "detailed": "Write a clear, well-structured answer with paragraphs. Include definitions, key concepts, and important details.",
                "comprehensive": "Provide detailed bullet points with explanations for each."
            }.get(explanation_level, "Write a clear, well-structured answer.")

            prompt = (
                f"You are an expert tutor. A student asked a question about their study material.\n"
                f"Below are the most relevant sections extracted from the document.\n"
                f"Rephrase this into a clear, organized answer to the question.\n"
                f"Do NOT copy verbatim. Explain it in your own words.\n"
                f"Do NOT use LaTeX or math notation. Write math concepts in plain English.\n"
                f"{length_inst}\n\n"
                f"RELEVANT SECTIONS:\n{context_for_llm}\n\n"
                f"QUESTION: {actual_query}\n\n"
                f"YOUR ANSWER:"
            )
            answer = self._call_llm(prompt, max_tokens=max_tok)
            if answer:
                return {"response": answer, "sources": sources}

            # Try shorter prompt
            print("LLM failed, retrying with shorter prompt")
            short_prompt = f"Summarize this in your own words:\n\n{context_for_llm[:1500]}\n\nQuestion: {actual_query}\nAnswer:"
            answer = self._call_llm(short_prompt, max_tokens=1000)
            if answer:
                return {"response": answer, "sources": sources}

            return {"response": "I found relevant sections in your document but the AI service is temporarily unavailable. Check the Sources section below for the relevant excerpts.", "sources": sources}

        # Document not relevant or no context - expand abbreviations and try web search
        search_query = actual_query
        clean_aq = re.sub(r'[?!.,;:]', '', actual_query).strip().lower()
        if clean_aq in expand_map:
            search_query = expand_map[clean_aq]
            print(f"Expanded '{actual_query}' to '{search_query}'")

        # Add context words for better search results
        if not any(w in search_query.lower() for w in ['what', 'how', 'why', 'when', 'where', 'explain', 'define', 'definition']):
            search_query = f"what is {search_query}"

        print(f"Searching web for: {search_query}")
        try:
            web_results = self._web_search(search_query)
        except Exception as e:
            print(f"Web search exception: {e}")
            web_results = None

        if web_results:
            print(f"Web search returned {len(web_results)} chars")
            web_sources = [{"content": web_results[:500], "metadata": {}, "type": "web"}]

            # Determine document topic from filename for context
            doc_topic = ""
            try:
                coll = self.chroma_client.get_collection(f"doc_{document_id}")
                sample = coll.get(limit=1)
                if sample['documents']:
                    doc_topic = sample['documents'][0][:200]
            except:
                pass

            prompt = (
                f"You are an expert tutor. Answer the question using ONLY the web search results below.\n"
                f"The student's document is about: {doc_topic[:300]}...\n"
                f"Provide a clear, well-structured answer with key definitions and details.\n\n"
                f"WEB SEARCH RESULTS:\n{web_results}\n\n"
                f"QUESTION: {search_query}\n\n"
                f"ANSWER:"
            )
            answer = self._call_llm(prompt, max_tokens=max_tok)

            if answer:
                return {"response": f"This isn't covered in your document, but here's what I found online:\n\n{answer}", "sources": web_sources}
            else:
                return {"response": f"This isn't covered in your document, but here's what I found online:\n\n{web_results[:2000]}", "sources": web_sources}

        # Nothing worked at all
        return {"response": "I couldn't find information about this topic. Please try rephrasing your question.", "sources": sources}

    def query_stream(self, document_id: str, query: str, explanation_level: str = "detailed",
                     conversation_history: List[Dict] = None):
        """Stream response token by token."""
        self._load_env()

        followup_words = {'longer', 'shorter', 'more', 'less', 'explain', 'elaborate',
                          'detail', 'summarize', 'again', 'simpler', 'easier', 'harder',
                          'better', 'differently', 'expand', 'continue', 'more detail',
                          'tell me more', 'go on', 'what else'}
        followup_phrases = ['did not understand', "didn't understand", 'didnt understand',
                            'not understand', 'confused', 'unclear', 'can you explain',
                            'what does that mean', 'what do you mean', 'say that again',
                            'repeat', 'simpler', 'easier', 'in simple terms', 'like im 5',
                            "like i'm 5", 'eli5', 'break it down', 'step by step',
                            'over my head', 'too complicated', 'too complex', 'too hard',
                            'too difficult', 'make it simple', 'dumb it down', 'plain english',
                            'i dont get', "i don't get", 'i dont understand', "i don't understand",
                            'not clear', 'bit confused', 'little confused', 'doesnt make sense',
                            "doesn't make sense", 'went over my head', 'went above my head']
        actual_query = query
        clean_q = re.sub(r'[?!.,;:]', '', query).strip().lower()

        is_followup = (clean_q in followup_words or len(clean_q.split()) <= 2 or
                       any(phrase in clean_q for phrase in followup_phrases))

        if is_followup and conversation_history:
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    prev = msg.get("content", "").strip()
                    if prev and prev.lower() != clean_q:
                        actual_query = prev + " " + query
                        break

        expand_map = {'ai': 'artificial intelligence', 'ml': 'machine learning',
                      'dl': 'deep learning', 'nn': 'neural network',
                      'cv': 'computer vision', 'nlp': 'natural language processing'}
        relevance_query = actual_query
        clean_aq = re.sub(r'[?!.,;:]', '', actual_query).strip().lower()
        for abbr, full in expand_map.items():
            if abbr == clean_aq or abbr + '?' == clean_aq:
                relevance_query = full
                break
            if re.search(r'\b' + abbr + r'\b', clean_aq):
                relevance_query = re.sub(r'\b' + abbr + r'\b', full, clean_aq)
                break

        # Step 1: Extract relevant chunks from document
        combined_context = ""
        sources = []
        all_chunks = []
        try:
            collection = self.chroma_client.get_collection(f"doc_{document_id}")
            results = collection.query(query_embeddings=[self.get_embedding(query)], n_results=10)
            if results['documents'] and results['documents'][0]:
                all_chunks = results['documents'][0]
                combined_context = "\n\n".join(all_chunks)
                sources = [{"content": doc[:500], "metadata": {}, "type": "document"} for doc in all_chunks]
        except Exception as e:
            print(f"Collection error: {e}")

        history_text = ""
        if conversation_history:
            for msg in conversation_history[-6:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_text += f"{role}: {msg.get('content', '')}\n"
        history_section = f"Conversation History:\n{history_text}\n" if history_text else ""

        max_tok = {"basic": 800, "comprehensive": 4000}.get(explanation_level, 3000)

        # Step 2: Check if document is relevant
        doc_relevant = False
        if combined_context:
            doc_relevant = self._check_relevance(relevance_query, combined_context)
            print(f"Doc relevant for '{relevance_query}': {doc_relevant}")

        # Step 3a: If relevant — LLM rephrases document chunks
        if doc_relevant and combined_context:
            print(f"Document has answer, rephrasing via LLM for: {actual_query}")

            # Clean and deduplicate chunks, fix OCR artifacts
            seen = set()
            clean_chunks = []
            for chunk in all_chunks:
                fixed = self._clean_ocr_text(chunk)
                if fixed not in seen and len(fixed) > 30:
                    seen.add(fixed)
                    clean_chunks.append(fixed)

            # Score chunks by relevance to query and pick the best ones
            query_words = set(self._tokenize(relevance_query))
            scored = []
            for c in clean_chunks:
                chunk_words = set(self._tokenize(c))
                overlap = len(query_words & chunk_words)
                scored.append((overlap, c))
            scored.sort(key=lambda x: -x[0])
            top_chunks = [c for _, c in scored[:4]]
            context_for_llm = "\n\n".join(top_chunks)

            length_inst = {
                "basic": "Give a concise 2-3 sentence summary.",
                "detailed": "Write a clear, well-structured answer with paragraphs. Include definitions, key concepts, and important details.",
                "comprehensive": "Provide detailed bullet points with explanations for each."
            }.get(explanation_level, "Write a clear, well-structured answer.")

            prompt = (
                f"You are an expert tutor. A student asked a question about their study material.\n"
                f"Below are the most relevant sections extracted from the document.\n"
                f"Rephrase this into a clear, organized answer to the question.\n"
                f"Do NOT copy verbatim. Explain it in your own words.\n"
                f"Do NOT use LaTeX or math notation. Write math concepts in plain English.\n"
                f"{length_inst}\n\n"
                f"RELEVANT SECTIONS:\n{context_for_llm}\n\n"
                f"QUESTION: {actual_query}\n\n"
                f"YOUR ANSWER:"
            )

            llm_response = ""
            for chunk in self._call_llm_stream(prompt, max_tokens=max_tok):
                llm_response += chunk
                yield {"type": "token", "content": chunk}

            if llm_response:
                yield {"type": "done", "sources": sources}
                return

            # LLM failed — try non-streaming as fallback, then stream it word by word
            print("Stream failed, trying non-streaming LLM")
            answer = self._call_llm(prompt, max_tokens=max_tok)
            if answer:
                for word in answer.split(' '):
                    yield {"type": "token", "content": word + " "}
                yield {"type": "done", "sources": sources}
                return

            # Try shorter prompt
            print("Non-streaming also failed, retrying with shorter prompt")
            short_prompt = (
                f"Summarize this in your own words:\n\n{context_for_llm[:1500]}\n\n"
                f"Question: {actual_query}\nAnswer:"
            )
            answer = self._call_llm(short_prompt, max_tokens=1000)
            if answer:
                for word in answer.split(' '):
                    yield {"type": "token", "content": word + " "}
                yield {"type": "done", "sources": sources}
                return

            # Total failure — show graceful message
            yield {"type": "token", "content": "I found relevant sections in your document but the AI service is temporarily unavailable. Check the Sources section below for the relevant excerpts."}
            yield {"type": "done", "sources": sources}
            return

        # Step 3b: Not in document — search the web
        search_query = actual_query
        clean_aq = re.sub(r'[?!.,;:]', '', actual_query).strip().lower()
        if clean_aq in expand_map:
            search_query = expand_map[clean_aq]

        if not any(w in search_query.lower() for w in ['what', 'how', 'why', 'when', 'where', 'explain', 'define']):
            search_query = f"what is {search_query}"

        web_results = None
        try:
            web_results = self._web_search(search_query)
        except:
            pass

        if web_results:
            web_sources = [{"content": web_results[:500], "metadata": {}, "type": "web"}]

            # Stream the preface first
            yield {"type": "token", "content": "This isn't covered in your document, but here's what I found online:\n\n"}

            prompt = (
                f"You are an expert tutor. Answer the question using the web search results below.\n"
                f"Provide a clear, well-structured answer with key definitions and details.\n\n"
                f"WEB SEARCH RESULTS:\n{web_results[:3000]}\n\n"
                f"QUESTION: {search_query}\n\n"
                f"ANSWER:"
            )

            llm_response = ""
            for chunk in self._call_llm_stream(prompt, max_tokens=max_tok):
                llm_response += chunk
                yield {"type": "token", "content": chunk}

            if llm_response:
                yield {"type": "done", "sources": web_sources}
            else:
                fallback = f"Here's what I found online:\n\n{web_results[:2000]}"
                for word in fallback.split(' '):
                    yield {"type": "token", "content": word + " "}
                yield {"type": "done", "sources": web_sources}
            return

        yield {"type": "token", "content": "I couldn't find information about this topic. Please try rephrasing your question."}
        yield {"type": "done", "sources": sources}
