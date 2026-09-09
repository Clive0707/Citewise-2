"""
Chat Interface Module
Reuses existing RAG logic for GPT-like chat interface
"""
import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .embeddings_gemini import embed_documents
from .vector_pinecone import PineconeVectorStore
from .llm_providers.factory import get_llm_provider
from .constants import get_model_for_role
from .sandbox import DOMAIN_WEIGHTS, _get_pinecone_store

logger = logging.getLogger(__name__)

# Minimum brand chunks threshold for quality warning
MIN_BRAND_CHUNKS = 3

# Analytics intent keywords
ANALYTICS_KEYWORDS = [
    "how many questions",
    "in which questions",
    "was cited",
    "citation",
    "citations",
    "coverage",
    "out of",
    "percentage",
    "count",
    "how often",
    "how many times",
    "cited",
    "mention",
    "mentions",
    "appear",
    "appeared",
    "appearance",
]


async def process_chat_message(
    session_id: str,
    content: str,
    scope: str,
    run_id: Optional[str] = None,
    sandbox_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process a chat message using RAG pipeline.
    Reuses existing RAG logic from sandbox.py.

    Args:
        session_id: Chat session ID
        content: User's message/question
        scope: "sandbox_only" | "sandbox_competitors" | "web_only"
        run_id: Optional sandbox run ID to link to

    Returns:
        Dict with content, citations, tokens_in, tokens_out, model_used
    """
    start_time = time.time()

    # Validate scope
    if scope not in ["sandbox_only", "sandbox_competitors", "web_only"]:
        raise ValueError(f"Invalid scope: {scope}")

    # Web scope not supported in v1
    if scope == "web_only":
        return {
            "content": "Web search is not yet supported. Please use 'sandbox_only' or 'sandbox_competitors' scope.",
            "citations": [],
            "tokens_in": 0,
            "tokens_out": 0,
            "model_used": None,
        }

    # Require run_id for sandbox scopes
    if not run_id:
        return {
            "content": "No sandbox run linked to this session. Please create a session with a valid run_id.",
            "citations": [],
            "tokens_in": 0,
            "tokens_out": 0,
            "model_used": None,
        }

    print(f"[CHAT] Processing message for session={session_id}, scope={scope}, run_id={run_id}")
    print(f"[CHAT] User message: {content[:200]}...")
    logger.info(f"[chat] Processing message for session={session_id}, scope={scope}, run_id={run_id}")
    logger.info(f"[chat] User message: {content[:200]}...")  # Log first 200 chars

    # Step 0: Detect intent - analytics vs content
    is_analytics = _detect_analytics_intent(content)
    print(f"[CHAT] Intent detected: {'analytics' if is_analytics else 'content'}")
    logger.info(f"[chat] Intent detected: {'analytics' if is_analytics else 'content'}")

    # If analytics intent, query database directly and skip RAG pipeline
    if is_analytics:
        return await _handle_analytics_query(content, run_id, sandbox_url, session_id)

    # Use RAG_ANSWERING model (same as sandbox pipeline)
    model_name = get_model_for_role("RAG_ANSWERING")
    llm = get_llm_provider(model_name)

    try:
        # Step 1: Fetch sandbox_brand chunks from database BEFORE vector search
        # This ensures we always have brand chunks even if they have low similarity scores
        brand_chunks_from_db = await _fetch_sandbox_brand_chunks_from_db(run_id)
        print(f"[CHAT] Fetched {len(brand_chunks_from_db)} sandbox_brand chunks from database")
        logger.info(f"[chat] Fetched {len(brand_chunks_from_db)} sandbox_brand chunks from database")

        # Step 2: Generate query embedding (reuse existing function)
        print(f"[CHAT] Generating query embedding...")
        logger.info(f"[chat] Generating query embedding...")
        [query_vector] = await embed_documents([content])
        print(f"[CHAT] Query embedding generated, vector length: {len(query_vector)}")
        logger.info(f"[chat] Query embedding generated, vector length: {len(query_vector)}")

        # Step 3: Retrieve chunks from Pinecone (reuse existing logic)
        pinecone_store = _get_pinecone_store()
        namespace = f"sandbox-{run_id}"
        print(f"[CHAT] Searching Pinecone namespace: {namespace}")
        logger.info(f"[chat] Searching Pinecone namespace: {namespace}")

        # Retrieve more chunks initially to allow for domain weighting
        top_k = 30
        print(f"[CHAT] Retrieving top {top_k} chunks from Pinecone...")
        logger.info(f"[chat] Retrieving top {top_k} chunks from Pinecone...")
        pinecone_chunks = await pinecone_store.search(
            namespace=namespace,
            query_vector=query_vector,
            top_k=top_k,
        )

        print(f"[CHAT] Retrieved {len(pinecone_chunks)} chunks from Pinecone")
        print(f"[CHAT] sandbox_url provided: {sandbox_url is not None}, value: {sandbox_url}")
        logger.info(f"[chat] Retrieved {len(pinecone_chunks)} chunks from Pinecone")

        # Step 4: Merge brand_chunks_from_db + pinecone_chunks, deduplicate by (url, chunk_id)
        retrieved_chunks = _merge_and_deduplicate_chunks(brand_chunks_from_db, pinecone_chunks)
        print(f"[CHAT] brand_chunks={len(brand_chunks_from_db)}, pinecone_chunks={len(pinecone_chunks)}, merged={len(retrieved_chunks)}")
        logger.info(f"[chat] brand_chunks={len(brand_chunks_from_db)}, pinecone_chunks={len(pinecone_chunks)}, merged={len(retrieved_chunks)}")
        
        # CRITICAL: Do NOT reclassify chunks during retrieval.
        # domain_type is FINALIZED at ingestion time (see sandbox.py:classify_domain_type and _persist_chunks_to_db).
        # Reclassification would break citation correctness and analytics consistency.
        # Trust the domain_type from the database - it was set correctly during chunk persistence.
        # If domain_type is missing or "unknown", default to "editorial" but do NOT reclassify based on runtime context.
        for chunk in retrieved_chunks:
            if not chunk.get("domain_type") or chunk.get("domain_type") == "unknown":
                chunk["domain_type"] = "editorial"
                logger.debug(f"[chat] Set default domain_type=editorial for chunk with missing type: {chunk.get('url', '')[:60]}")
        
        if retrieved_chunks:
            # Log chunk details (domain_type is from ingestion, not reclassified)
            domain_types = {}
            print(f"[CHAT] Sample chunks (first 5) with domain_type from ingestion:")
            for i, chunk in enumerate(retrieved_chunks[:5], 1):  # Log first 5 chunks
                domain_type = chunk.get("domain_type", "editorial")
                is_client = chunk.get("is_client", False)
                domain_types[domain_type] = domain_types.get(domain_type, 0) + 1
                chunk_info = (
                    f"  Chunk {i}: url={chunk.get('url', 'N/A')[:80]}, "
                    f"domain_type={domain_type}, is_client={is_client}, score={chunk.get('score', 0):.3f}, "
                    f"text_preview={chunk.get('text', '')[:100]}..."
                )
                print(f"[CHAT] {chunk_info}")
                logger.info(f"[chat] Chunk sample: {chunk_info}")
            
            # Count all domain types
            all_domain_types = {}
            for chunk in retrieved_chunks:
                dt = chunk.get("domain_type", "editorial")
                all_domain_types[dt] = all_domain_types.get(dt, 0) + 1
            print(f"[CHAT] Domain type distribution (all {len(retrieved_chunks)} chunks): {all_domain_types}")
            logger.info(f"[chat] Domain type distribution: {all_domain_types}")

        if not retrieved_chunks:
            print(f"[CHAT] ERROR: No chunks retrieved from Pinecone namespace: {namespace}")
            logger.warning(f"[chat] No chunks retrieved from Pinecone namespace: {namespace}")
            return {
                "content": "No relevant content found in the sandbox. Please ensure the sandbox run has completed and contains chunks.",
                "citations": [],
                "tokens_in": estimate_tokens(content),
                "tokens_out": 0,
                "model_used": model_name,
            }

        # Step 3: Apply domain filtering based on scope
        print(f"[CHAT] Applying scope filter: {scope}")
        print(f"[CHAT] Chunks before filtering: {len(retrieved_chunks)}")
        domain_types_before_filter = {}
        for chunk in retrieved_chunks:
            dt = chunk.get("domain_type", "editorial")
            domain_types_before_filter[dt] = domain_types_before_filter.get(dt, 0) + 1
        print(f"[CHAT] Domain types before filter: {domain_types_before_filter}")
        logger.info(f"[chat] Applying scope filter: {scope}")
        logger.info(f"[chat] Chunks before filtering: {len(retrieved_chunks)}")
        logger.info(f"[chat] Domain types before filter: {domain_types_before_filter}")
        
        if scope == "sandbox_only":
            # Filter to only sandbox_brand chunks
            before_count = len(retrieved_chunks)
            domain_types_before = {}
            for c in retrieved_chunks:
                dt = c.get("domain_type", "unknown")
                domain_types_before[dt] = domain_types_before.get(dt, 0) + 1
            print(f"[CHAT] Domain types before filter: {domain_types_before}")
            
            retrieved_chunks = [
                c for c in retrieved_chunks
                if c.get("domain_type") == "sandbox_brand"
            ]
            print(f"[CHAT] After sandbox_only filter: {len(retrieved_chunks)}/{before_count} chunks (filtered for domain_type='sandbox_brand')")
            logger.info(f"[chat] After sandbox_only filter: {len(retrieved_chunks)}/{before_count} chunks (filtered for domain_type='sandbox_brand')")
        elif scope == "sandbox_competitors":
            # Filter to sandbox_brand and business_competitor
            before_count = len(retrieved_chunks)
            domain_types_before = {}
            for c in retrieved_chunks:
                dt = c.get("domain_type", "unknown")
                domain_types_before[dt] = domain_types_before.get(dt, 0) + 1
            print(f"[CHAT] Domain types before filter: {domain_types_before}")
            
            retrieved_chunks = [
                c for c in retrieved_chunks
                if c.get("domain_type") in ["sandbox_brand", "business_competitor"]
            ]
            print(f"[CHAT] After sandbox_competitors filter: {len(retrieved_chunks)}/{before_count} chunks (filtered for domain_type in ['sandbox_brand', 'business_competitor'])")
            logger.info(f"[chat] After sandbox_competitors filter: {len(retrieved_chunks)}/{before_count} chunks (filtered for domain_type in ['sandbox_brand', 'business_competitor'])")

        # Log final count after scope filtering
        final_count = len(retrieved_chunks)
        print(f"[CHAT] final={final_count} (after scope={scope} filter)")
        logger.info(f"[chat] final={final_count} (after scope={scope} filter)")
        
        if not retrieved_chunks:
            print(f"[CHAT] ERROR: No chunks after filtering! Scope={scope}")
            logger.warning(f"[chat] No chunks after filtering for scope={scope}")
            
            # Provide a helpful error message based on the issue
            scope_name = "sandbox only" if scope == "sandbox_only" else "sandbox and competitors"
            error_msg = f"No relevant content found for {scope_name} scope. "
            if scope == "sandbox_only":
                error_msg += "No sandbox brand chunks were found in the database for this run. "
            elif scope == "sandbox_competitors":
                error_msg += "No sandbox brand or competitor chunks were found. "
            error_msg += "Please ensure your sandbox run has completed successfully and contains properly classified content."
            
            return {
                "content": error_msg,
                "citations": [],
                "tokens_in": estimate_tokens(content),
                "tokens_out": 0,
                "model_used": model_name,
            }
        
        # Check if we have enough brand chunks for quality warning
        brand_chunk_count = sum(1 for c in retrieved_chunks if c.get("domain_type") == "sandbox_brand")
        if brand_chunk_count < MIN_BRAND_CHUNKS and scope in ["sandbox_only", "sandbox_competitors"]:
            print(f"[CHAT] WARNING: Only {brand_chunk_count} sandbox_brand chunks available (minimum recommended: {MIN_BRAND_CHUNKS})")
            logger.warning(f"[chat] Only {brand_chunk_count} sandbox_brand chunks available (minimum recommended: {MIN_BRAND_CHUNKS})")

        # Step 4: Apply domain weights (reuse existing logic)
        logger.info(f"[chat] Applying domain weights to {len(retrieved_chunks)} chunks...")
        weighted_chunks = []
        for chunk in retrieved_chunks:
            domain_type = chunk.get("domain_type", "editorial")
            original_score = chunk.get("score", 0.0)
            weight = DOMAIN_WEIGHTS.get(domain_type, 0.8)
            weighted_score = original_score * weight
            weighted_chunks.append({
                **chunk,
                "original_score": original_score,
                "weighted_score": weighted_score,
                "domain_type": domain_type,
            })
            logger.debug(f"[chat] Chunk weighted: domain_type={domain_type}, original={original_score:.3f}, weight={weight}, weighted={weighted_score:.3f}")

        # Sort by weighted score
        weighted_chunks.sort(key=lambda x: x["weighted_score"], reverse=True)
        logger.info(f"[chat] Top 3 weighted chunks: {[(c.get('url', 'N/A')[:50], c.get('weighted_score', 0)) for c in weighted_chunks[:3]]}")

        # Step 5: Retrieval balancing (ensure at least 1 brand chunk if available)
        final_chunks = []
        brand_chunks = [c for c in weighted_chunks if c["domain_type"] in ["sandbox_brand", "business_competitor"]]
        editorial_chunks = [c for c in weighted_chunks if c["domain_type"] == "editorial"]

        if brand_chunks:
            top_brand = brand_chunks[0]
            if top_brand not in weighted_chunks[:10]:
                final_chunks.append(top_brand)

        # Add top weighted chunks (avoid duplicates)
        seen_urls = set()
        for chunk in weighted_chunks:
            if len(final_chunks) >= 10:
                break
            chunk_url = chunk.get("url", "")
            if chunk_url not in seen_urls:
                final_chunks.append(chunk)
                seen_urls.add(chunk_url)

        logger.info(f"[chat] Final chunks after balancing: {len(final_chunks)}")
        logger.info(f"[chat] Final chunk URLs: {[c.get('url', 'N/A')[:60] for c in final_chunks[:5]]}")

        # Step 6: Build RAG context (reuse existing prompt structure)
        logger.info(f"[chat] Building RAG context from {len(final_chunks)} chunks...")
        context_parts = []
        total_context_length = 0
        for i, chunk in enumerate(final_chunks, 1):
            chunk_text = chunk.get("text", "")
            chunk_url = chunk.get("url", "")
            chunk_length = len(chunk_text)
            total_context_length += chunk_length
            context_parts.append(f"[Source {i}: {chunk_url}]\n{chunk_text}")
            logger.debug(f"[chat] Context chunk {i}: url={chunk_url[:60]}, length={chunk_length} chars")

        context = "\n\n".join(context_parts)
        logger.info(f"[chat] Total context length: {total_context_length} characters ({len(context)} chars with formatting)")

        # Step 7: Build system prompt (reuse existing logic with scope awareness)
        # Check if we need to add quality warning
        brand_chunk_count = sum(1 for c in final_chunks if c.get("domain_type") == "sandbox_brand")
        quality_warning = ""
        if brand_chunk_count < MIN_BRAND_CHUNKS and scope in ["sandbox_only", "sandbox_competitors"]:
            quality_warning = f"\n\nNOTE: Limited sandbox brand data available ({brand_chunk_count} chunks); answer may be incomplete.\n"
        
        system_prompt = (
            "You are a helpful AI assistant that answers questions based on the provided context.\n\n"
            "CONTEXT:\n"
            f"{context}\n\n"
            "RULES:\n"
            "1. Answer ONLY based on the provided context.\n"
            "2. If the context doesn't contain enough information, say so clearly.\n"
            "3. Cite sources using the format [Source N] when referencing information.\n"
            "4. Be concise and factual.\n"
            "5. Do not make up information not present in the context.\n"
        )
        
        # Add quality warning if needed
        if quality_warning:
            system_prompt += quality_warning

        # Add scope-specific instructions
        if scope == "sandbox_only":
            system_prompt += "\n6. Focus on the sandbox brand content. This is the primary source.\n"
        elif scope == "sandbox_competitors":
            system_prompt += (
                "\n6. You have access to both sandbox brand and competitor content. "
                "Prefer citing sandbox brand when relevant, but competitor information is also valuable.\n"
            )

        # Step 8: Call LLM (reuse existing provider)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]

        # Estimate tokens before call
        prompt_text = system_prompt + "\n\n" + content
        tokens_in_estimate = estimate_tokens(prompt_text)

        # Call LLM
        response_text = await llm.chat(
            messages=messages,
            max_tokens=2000,
        )

        # Estimate tokens after call
        tokens_out_estimate = estimate_tokens(response_text)

        # Step 9: Extract citations (match URLs from context)
        citations = []
        for chunk in final_chunks:
            url = chunk.get("url", "")
            domain_type = chunk.get("domain_type", "editorial")
            chunk_id = chunk.get("chunk_id", 0)
            relevance_score = chunk.get("weighted_score", 0.0)

            # Check if URL is mentioned in response
            if url in response_text or any(part in response_text for part in url.split("/")[-2:]):
                citations.append({
                    "url": url,
                    "domain_type": domain_type,
                    "chunk_id": chunk_id,
                    "relevance_score": round(relevance_score, 3),
                })

        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[chat] Completed session={session_id}, "
            f"tokens_in={tokens_in_estimate}, tokens_out={tokens_out_estimate}, "
            f"citations={len(citations)}, latency_ms={latency_ms}"
        )

        return {
            "content": response_text,
            "citations": citations,
            "tokens_in": tokens_in_estimate,
            "tokens_out": tokens_out_estimate,
            "model_used": model_name,
        }

    except Exception as e:
        logger.error(f"[chat] Error processing message for session={session_id}: {e}", exc_info=True)
        return {
            "content": f"Sorry, I encountered an error: {str(e)}",
            "citations": [],
            "tokens_in": estimate_tokens(content),
            "tokens_out": 0,
            "model_used": model_name,
        }


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation: 1 token ≈ 4 characters.
    This is a fallback if LLM provider doesn't return usage metadata.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def _detect_analytics_intent(content: str) -> bool:
    """
    Detect if the query is analytics-based (counting, citations) vs content-based (RAG).
    
    Args:
        content: User's question/message
        
    Returns:
        True if analytics intent detected, False for content/RAG intent
    """
    content_lower = content.lower()
    
    # Check for analytics keywords
    for keyword in ANALYTICS_KEYWORDS:
        if keyword in content_lower:
            return True
    
    return False


async def _handle_analytics_query(
    content: str,
    run_id: str,
    sandbox_url: Optional[str],
    session_id: str,
) -> Dict[str, Any]:
    """
    Handle analytics queries by querying sandbox_rag_results directly.
    Skips RAG pipeline entirely.
    
    Args:
        content: User's analytics question
        run_id: Sandbox run ID
        sandbox_url: Sandbox URL (for extracting domain)
        session_id: Chat session ID
        
    Returns:
        Dict with content, citations, tokens_in, tokens_out, model_used
    """
    start_time = time.time()
    
    try:
        # Extract brand domain from sandbox_url
        brand_domain = None
        if sandbox_url:
            parsed = urlparse(sandbox_url)
            brand_domain = parsed.netloc.lower().replace("www.", "")
        
        print(f"[CHAT] Processing analytics query: {content[:100]}...")
        logger.info(f"[chat] Processing analytics query: {content[:100]}...")
        
        # Query backend API for analytics data
        backend_url = os.getenv("BACKEND_BASE_URL", "http://localhost:4000")
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Get questions where brand was cited
            questions_with_brand = await _get_questions_where_brand_cited(client, backend_url, run_id, brand_domain)
            
            # Get citation count
            citation_count = len(questions_with_brand)
            
            # Get total question count
            total_questions = await _get_total_question_count(client, backend_url, run_id)
            
            # Format response
            answer = _format_analytics_answer(
                content=content,
                questions_with_brand=questions_with_brand,
                citation_count=citation_count,
                total_questions=total_questions,
                brand_domain=brand_domain,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            print(f"[CHAT] Analytics query completed: citation_count={citation_count}, total_questions={total_questions}")
            logger.info(f"[chat] Analytics query completed: citation_count={citation_count}, total_questions={total_questions}")
            
            return {
                "content": answer,
                "citations": [],  # Analytics queries don't need chunk citations
                "tokens_in": estimate_tokens(content),
                "tokens_out": estimate_tokens(answer),
                "model_used": None,  # No LLM used for analytics
            }
    except Exception as e:
        logger.error(f"[chat] Error processing analytics query: {e}", exc_info=True)
        return {
            "content": f"Sorry, I encountered an error processing your analytics query: {str(e)}",
            "citations": [],
            "tokens_in": estimate_tokens(content),
            "tokens_out": 0,
            "model_used": None,
        }


async def _get_questions_where_brand_cited(
    client: Any,
    backend_url: str,
    run_id: str,
    brand_domain: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Get list of questions where brand was cited.
    
    Args:
        client: httpx.AsyncClient instance
        backend_url: Backend API URL
        run_id: Sandbox run ID
        brand_domain: Brand domain to search for (e.g., "zomato.com")
        
    Returns:
        List of question dicts with question text and answer info
    """
    try:
        params = {"run_id": run_id}
        if brand_domain:
            params["brand_domain"] = brand_domain
        
        resp = await client.get(
            f"{backend_url}/api/sandbox/analytics/questions-with-brand",
            params=params,
            timeout=10.0,
        )
        
        if resp.status_code == 200:
            data = resp.json()
            return data.get("questions", [])
        else:
            logger.warning(f"[chat] Backend API returned {resp.status_code} for questions-with-brand")
            return []
    except Exception as e:
        logger.error(f"[chat] Error fetching questions with brand: {e}")
        return []


async def _get_total_question_count(
    client: Any,
    backend_url: str,
    run_id: str,
) -> int:
    """
    Get total number of questions in the run.
    
    Args:
        client: httpx.AsyncClient instance
        backend_url: Backend API URL
        run_id: Sandbox run ID
        
    Returns:
        Total question count
    """
    try:
        resp = await client.get(
            f"{backend_url}/api/sandbox/analytics/total-questions",
            params={"run_id": run_id},
            timeout=10.0,
        )
        
        if resp.status_code == 200:
            data = resp.json()
            return data.get("total", 0)
        else:
            logger.warning(f"[chat] Backend API returned {resp.status_code} for total-questions")
            return 0
    except Exception as e:
        logger.error(f"[chat] Error fetching total question count: {e}")
        return 0


def _format_analytics_answer(
    content: str,
    questions_with_brand: List[Dict[str, Any]],
    citation_count: int,
    total_questions: int,
    brand_domain: Optional[str],
) -> str:
    """
    Format analytics data into natural language answer.
    
    Args:
        content: Original user question
        questions_with_brand: List of questions where brand was cited
        citation_count: Number of questions with citations
        total_questions: Total number of questions
        brand_domain: Brand domain name
        
    Returns:
        Formatted natural language answer
    """
    content_lower = content.lower()
    
    # Determine what the user is asking for
    if "in which questions" in content_lower or "which questions" in content_lower:
        # List the questions
        if citation_count == 0:
            return f"Your website was not cited in any of the {total_questions} questions in this run."
        
        question_list = "\n".join([f"{i+1}. {q.get('question', 'N/A')}" for i, q in enumerate(questions_with_brand)])
        return f"Your website was cited in {citation_count} out of {total_questions} questions:\n\n{question_list}"
    
    elif "how many" in content_lower or "count" in content_lower:
        # Return count
        if citation_count == 0:
            return f"Your website was cited in 0 out of {total_questions} questions."
        return f"Your website was cited in {citation_count} out of {total_questions} questions."
    
    elif "was cited only once" in content_lower or "cited only once" in content_lower:
        # Check if cited exactly once
        if citation_count == 1:
            return f"Yes, your website was cited in exactly 1 question out of {total_questions}."
        elif citation_count == 0:
            return f"No, your website was not cited in any of the {total_questions} questions."
        else:
            return f"No, your website was cited in {citation_count} questions out of {total_questions}."
    
    elif "percentage" in content_lower or "%" in content_lower:
        # Calculate percentage
        if total_questions == 0:
            return "No questions found in this run."
        percentage = (citation_count / total_questions) * 100
        return f"Your website was cited in {citation_count} out of {total_questions} questions ({percentage:.1f}%)."
    
    else:
        # Generic answer
        if citation_count == 0:
            return f"Your website was not cited in any of the {total_questions} questions in this run."
        question_list = "\n".join([f"{i+1}. {q.get('question', 'N/A')}" for i, q in enumerate(questions_with_brand[:10])])  # Limit to 10
        if citation_count > 10:
            question_list += f"\n\n... and {citation_count - 10} more questions."
        return f"Your website was cited in {citation_count} out of {total_questions} questions:\n\n{question_list}"


async def _fetch_sandbox_brand_chunks_from_db(run_id: str) -> List[Dict[str, Any]]:
    """
    Fetch sandbox_brand chunks directly from database.
    This ensures we always have brand chunks even if they have low vector similarity scores.
    
    Args:
        run_id: Sandbox run ID
        
    Returns:
        List of chunk dicts in same format as Pinecone results
    """
    # Always use backend API (has proper database permissions via Prisma)
    # Supabase client may have permission issues, so we route through backend
    backend_url = os.getenv("BACKEND_BASE_URL", "http://localhost:4000")
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{backend_url}/api/sandbox/chunks",
                params={"run_id": run_id, "domain_type": "sandbox_brand", "limit": 10},
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                chunks = []
                for row in data.get("chunks", []):
                    chunks.append({
                        "url": row.get("url", ""),
                        "text": row.get("text", ""),
                        "chunk_id": row.get("chunk_id", 0),
                        "is_client": row.get("is_client", False),
                        "domain": row.get("domain", ""),
                        "summary": row.get("summary", ""),
                        "domain_type": row.get("domain_type", "sandbox_brand"),
                        "score": 1.0,
                    })
                logger.info(f"[chat] Fetched {len(chunks)} sandbox_brand chunks from backend API")
                return chunks
            else:
                logger.warning(f"[chat] Backend API returned {resp.status_code}, falling back to empty list")
                return []
    except Exception as api_error:
        logger.warning(f"[chat] Backend API call failed: {api_error}, falling back to empty list")
        return []


def _merge_and_deduplicate_chunks(
    brand_chunks: List[Dict[str, Any]],
    pinecone_chunks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge brand chunks from DB with Pinecone chunks, deduplicating by (url, chunk_id).
    Preserves highest score per chunk.
    
    Args:
        brand_chunks: Chunks fetched from database
        pinecone_chunks: Chunks from Pinecone vector search
        
    Returns:
        Merged and deduplicated list of chunks
    """
    # Use dict keyed by (url, chunk_id) to deduplicate
    chunk_map: Dict[tuple, Dict[str, Any]] = {}
    
    # First, add brand chunks (these have priority)
    for chunk in brand_chunks:
        key = (chunk.get("url", ""), chunk.get("chunk_id", 0))
        if key not in chunk_map:
            chunk_map[key] = chunk
        else:
            # Keep chunk with higher score
            if chunk.get("score", 0.0) > chunk_map[key].get("score", 0.0):
                chunk_map[key] = chunk
    
    # Then, add Pinecone chunks (may overwrite if same key but lower score)
    for chunk in pinecone_chunks:
        key = (chunk.get("url", ""), chunk.get("chunk_id", 0))
        if key not in chunk_map:
            chunk_map[key] = chunk
        else:
            # Keep chunk with higher score
            if chunk.get("score", 0.0) > chunk_map[key].get("score", 0.0):
                chunk_map[key] = chunk
    
    return list(chunk_map.values())



