"""
Compare content extraction methods: Our approach vs LLM with web access.

Tests both approaches on the same set of URLs and compares:
- Latency
- Cost (token usage)
- Output quality
- Success rate

Uses OpenAI Responses API with web_search tool for Method B.
"""

import time
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openai import OpenAI
from technoshare_commentator.config import get_settings
from technoshare_commentator.retrieval.fetch import fetcher
from technoshare_commentator.retrieval.extract import extract_content, create_snippets
from technoshare_commentator.llm.analyze import run_analysis
from technoshare_commentator.schemas.evidence import EvidencePack, EvidenceSource
from technoshare_commentator.llm.schema import AnalysisResult

settings = get_settings()
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Test URLs (using sites that allow scraping)
TEST_URLS = [
    "https://arstechnica.com/information-technology/2026/01/openai-to-test-ads-in-chatgpt-as-it-burns-through-billions/",
    "https://github.com/facebookresearch/sam-3d-objects",
    "https://arxiv.org/abs/2406.08598",
    "https://www.aboutamazon.com/news/aws/aws-amazon-bedrock-agent-core-ai-agents",
]


class ExperimentResult:
    """Stores results for one experiment run."""
    
    def __init__(self, url: str, method: str):
        self.url = url
        self.method = method
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.success = False
        self.error: Optional[str] = None
        self.tokens_input: Optional[int] = None
        self.tokens_output: Optional[int] = None
        self.cost_usd: Optional[float] = None
        self.output: Optional[Dict[str, Any]] = None
        
        # NEW: Additional tracking
        self.reference_snippets: Optional[List[Dict[str, Any]]] = None  # for A (strict judging)
        self.web_sources: Optional[List[Dict[str, Any]]] = None         # for B (sources used)
        self.quality: Optional[Dict[str, Any]] = None                   # judge outputs
    
    def finish(self, success: bool, error: Optional[str] = None):
        self.end_time = time.time()
        self.success = success
        self.error = error
    
    @property
    def latency(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "method": self.method,
            "success": self.success,
            "latency_seconds": round(self.latency, 2),
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "cost_usd": self.cost_usd,
            "error": self.error,
            "output": self.output,
            "reference_snippets": self.reference_snippets,
            "web_sources": self.web_sources,
            "quality": self.quality,
        }


# -------------------------
# Helpers for Responses API
# -------------------------

def _safe_json_loads(s: str) -> Dict[str, Any]:
    """Safe JSON parsing with error handling."""
    return json.loads(s.strip())


def _extract_web_sources_from_responses(resp) -> List[Dict[str, Any]]:
    """
    Extract sources when you set include=["web_search_call.action.sources"].
    The Responses API returns a list of output items, including web_search_call items.
    """
    sources: List[Dict[str, Any]] = []
    output_items = getattr(resp, "output", None) or []
    
    for item in output_items:
        itype = getattr(item, "type", None)
        if itype != "web_search_call":
            continue
        action = getattr(item, "action", None)
        if not action:
            continue
        action_sources = getattr(action, "sources", None)
        if action_sources:
            # Convert sources to dict for JSON serialization
            for src in action_sources:
                sources.append({
                    "url": getattr(src, "url", None),
                    "title": getattr(src, "title", None),
                    "snippet": getattr(src, "snippet", None),
                })
    
    return sources


# -------------------------
# Method A: HTML -> LLM (no web)
# -------------------------

def method_A_html_to_llm(url: str) -> ExperimentResult:
    """A: Fetch HTML → Extract → Pass snippets/content to LLM (no web access)."""
    result = ExperimentResult(url, "method_A_html_no_web")
    
    try:
        # 1. Fetch HTML
        print(f"  Fetching {url}...")
        html = fetcher.fetch_url(url)
        
        # 2. Extract content
        print(f"  Extracting content...")
        extracted = extract_content(html, url)
        text = extracted.get("text", "")
        
        if not text:
            result.finish(False, "Failed to extract content")
            return result
        
        # 3. Create snippets (same as pipeline)
        snippets = create_snippets(text, url, max_snippets=12)
        result.reference_snippets = snippets  # NEW: store for strict judging
        
        # Create EvidencePack for run_analysis
        from datetime import datetime
        evidence = EvidencePack(
            sources=[EvidenceSource(url=url, title=extracted.get("title") or "Article", fetched_at=datetime.now().isoformat())],
            snippets=snippets,
            coverage="full"
        )
        
        # 4. Call LLM with our prompt
        print(f"  Analyzing with LLM (no web tool)...")
        analysis_result = run_analysis(evidence)
        
        # run_analysis returns AnalysisResult (Pydantic model)
        result_dict = analysis_result.model_dump()
        
        # Calculate cost (GPT-4o pricing: $2.50/1M input, $10/1M output)
        input_tokens = len(text) // 4  # Rough estimate: 1 token ≈ 4 chars
        output_tokens = len(json.dumps(result_dict)) // 4
        
        result.tokens_input = input_tokens
        result.tokens_output = output_tokens
        result.cost_usd = (input_tokens / 1_000_000 * 2.50) + (output_tokens / 1_000_000 * 10.00)
        result.output = result_dict
        result.finish(True)
        
    except Exception as e:
        print(f"  Error: {e}")
        result.finish(False, str(e))
    
    return result


# -------------------------
# Method B: URL -> LLM (with web_search tool)
# -------------------------

def method_B_url_with_web(url: str) -> ExperimentResult:
    """B: Pass URL directly to LLM; allow web access via Responses API web_search."""
    result = ExperimentResult(url, "method_B_url_with_web")
    
    try:
        print(f"  Calling LLM with web_search for {url}...")
        
        system_prompt = """You are an AI analyst.
Goal: Produce the best possible answer. You may use web search.

Return ONLY a JSON object:
{
  "tldr": ["sentence 1", "sentence 2", "sentence 3"],
  "summary": "5-10 sentence paragraph",
  "projects": ["**Project 1** — description", "..."],
  "similar_tech": ["**Tech 1** — description", "..."]
}
"""
        
        user_prompt = f"""Analyze the content at this URL:
{url}

Use web search to fetch and read it (and other authoritative sources if helpful).
Return ONLY the JSON object."""
        
        resp = client.responses.create(
            model=settings.MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[{"type": "web_search"}],  # enable web access
            tool_choice="auto",
            include=["web_search_call.action.sources"],  # log sources
            temperature=0.0,
        )
        
        # Usage (Responses API)
        if getattr(resp, "usage", None):
            result.tokens_input = getattr(resp.usage, "input_tokens", None)
            result.tokens_output = getattr(resp.usage, "output_tokens", None)
            if result.tokens_input and result.tokens_output:
                result.cost_usd = (result.tokens_input / 1_000_000 * 2.50) + (result.tokens_output / 1_000_000 * 10.00)
        
        result.output = _safe_json_loads(resp.output_text)
        result.web_sources = _extract_web_sources_from_responses(resp)
        result.finish(True)
        
    except Exception as e:
        print(f"  Error: {e}")
        result.finish(False, str(e))
    
    return result


# -------------------------
# Quality assessment: Term-grounded relevance
# -------------------------

def _flatten_candidate(output: Dict[str, Any]) -> str:
    """Convert JSON output into a single text blob for judging."""
    parts = []
    if isinstance(output.get("tldr"), list):
        parts.extend(output["tldr"])
    for k in ("summary",):
        if output.get(k):
            parts.append(str(output[k]))
    for k in ("projects", "similar_tech"):
        v = output.get(k)
        if isinstance(v, list):
            parts.extend([str(x) for x in v])
    return "\n".join(parts).strip()


def extract_page_terms(reference_snippets: List[Dict[str, Any]], *, model: str) -> Dict[str, Any]:
    """
    Extract key terms/entities/concepts that are explicitly mentioned in the page snippets.
    Output is deterministic-ish (temp 0), and acts as your 'what is being mentioned' anchor.
    """
    system = """You extract key terms/entities/concepts from page snippets.

Rules:
- Only include terms that are explicitly present in the snippets.
- Prefer product names, acronyms, libraries, model names, standards, companies, and core concepts.
- Return 8–15 terms max.
Return ONLY JSON:
{
  "terms": [
    {"term":"...", "snippet_evidence":"short quote fragment or paraphrase from snippets"}
  ]
}
"""

    payload = {"snippets": reference_snippets}

    r = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload)},
        ],
        temperature=0.0,
    )
    return _safe_json_loads(r.output_text)


def assess_term_grounded_relevance(
    *,
    url: str,
    reference_snippets: List[Dict[str, Any]],
    output_A: Dict[str, Any],
    output_B: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Quality metric optimized for: 'provide relevant information about what is mentioned on the page'.
    Judge is allowed to use web_search to verify correctness / add context when grading.
    """

    # Step 1: extract what the page actually mentions (anchor)
    print("    Extracting page terms...")
    term_pack = extract_page_terms(reference_snippets, model=settings.MODEL)
    terms = term_pack.get("terms", [])

    judge_system = f"""You are grading candidate outputs for: TERM-GROUNDED RELEVANCE.

Goal:
- The candidate should give relevant, correct, helpful context about the key terms mentioned on the page.
- It's OK to add info not in the page, BUT it must stay focused on those terms and be correct.

Score 0-10:
- term_coverage: addressed most terms with meaningful detail
- correctness: statements about terms are correct (you may verify on web)
- helpful_context: adds useful background/implications (not generic)
- relevance: stays anchored to the extracted terms, minimal drift
- actionability: good concrete project ideas / tech mapping based on terms
- format_compliance: valid JSON shape in candidate (assume it is JSON already)

Return ONLY JSON:
{{
  "scores": {{
    "term_coverage": 0-10,
    "correctness": 0-10,
    "helpful_context": 0-10,
    "relevance": 0-10,
    "actionability": 0-10,
    "overall": 0-10
  }},
  "missed_terms": ["..."],
  "notable_errors": ["..."],
  "drift_topics": ["..."],
  "verdict": "one short sentence"
}}

URL: {url}
Focus areas: {project_context.get('focus_areas', [])}
"""

    def grade(candidate: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "page_terms": terms,
            "candidate_text": _flatten_candidate(candidate),
            "candidate_json": candidate,
        }

        r = client.responses.create(
            model=settings.MODEL,
            input=[
                {"role": "system", "content": judge_system},
                {"role": "user", "content": json.dumps(payload)},
            ],
            tools=[{"type": "web_search"}],
            tool_choice="auto",
            include=["web_search_call.action.sources"],
            temperature=0.0,
        )
        out = _safe_json_loads(r.output_text)
        out["_judge_web_sources"] = _extract_web_sources_from_responses(r)
        return out

    print("    Grading A (term-grounded)...")
    qa = grade(output_A)
    
    print("    Grading B (term-grounded)...")
    qb = grade(output_B)

    return {
        "page_terms": term_pack,
        "A_term_grounded": qa,
        "B_term_grounded": qb,
    }


# -------------------------
# Run loop
# -------------------------

def run_experiment():
    """Run the experiment on all test URLs."""
    print("=" * 80)
    print("EXPERIMENT: A (HTML->LLM, no web) vs B (URL->LLM, web_search)")
    print("=" * 80)
    print()
    
    # Load project context
    
    for i, url in enumerate(TEST_URLS, 1):
        print(f"\n[{i}/{len(TEST_URLS)}] Testing URL: {url}")
        print("-" * 80)
        
        # Test Method A: Our approach
        print("\n  OPTION A: HTML content given to LLM (no web access)")
        resA = method_A_html_to_llm(url)
        results.append(resA)
        
        print(f"    ✓ Completed in {resA.latency:.2f}s")
        if resA.success:
            print(f"    Tokens: {resA.tokens_input} in / {resA.tokens_output} out")
            print(f"    Cost: ${resA.cost_usd:.4f}")
        else:
            print(f"    ✗ Failed: {resA.error}")
        
        # Test Method B: LLM with web access
        print("\n  OPTION B: URL given to LLM (with web access)")
        resB = method_B_url_with_web(url)
        results.append(resB)
        
        print(f"    ✓ Completed in {resB.latency:.2f}s")
        if resB.success:
            print(f"    Tokens: {resB.tokens_input} in / {resB.tokens_output} out")
            print(f"    Cost: ${resB.cost_usd:.4f}")
            if resB.web_sources:
                print(f"    Web sources used: {len(resB.web_sources)}")
        else:
            print(f"    ✗ Failed: {resB.error}")
        
        # Brief comparison
        if resA.success and resB.success:
            print(f"\n  COMPARISON:")
            print(f"    Latency: A = {resA.latency:.2f}s, B = {resB.latency:.2f}s")
            print(f"    Cost: A = ${resA.cost_usd:.4f}, B = ${resB.cost_usd:.4f}")
        
        # Quality assessment (only if both succeeded and we have reference snippets)
        if resA.success and resB.success and resA.reference_snippets and resA.output and resB.output:
            print("\n  QUALITY ASSESSMENT (term-grounded relevance)")
            q = assess_term_grounded_relevance(
                url=url,
                reference_snippets=resA.reference_snippets,
                output_A=resA.output,
                output_B=resB.output,
            )
            
            # Attach quality to results
            resA.quality = {"term_grounded": q["A_term_grounded"], "page_terms": q["page_terms"]}
            resB.quality = {"term_grounded": q["B_term_grounded"], "page_terms": q["page_terms"]}
            
            print(f"    A overall: {q['A_term_grounded']['scores']['overall']}/10")
            print(f"    B overall: {q['B_term_grounded']['scores']['overall']}/10")
    
    # Save results
    save_results(results)
    
    # Print summary
    print_summary(results)


def save_results(results: List[ExperimentResult]):
    """Save experiment results to JSON file."""
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = results_dir / f"extraction_comparison_{timestamp}.json"
    
    data = {
        "timestamp": timestamp,
        "test_urls": TEST_URLS,
        "results": [r.to_dict() for r in results]
    }
    
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"\n\n✓ Results saved to: {filename}")


def print_summary(results: List[ExperimentResult]):
    """Print summary statistics."""
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    methodA_results = [r for r in results if r.method == "method_A_html_no_web"]
    methodB_results = [r for r in results if r.method == "method_B_url_with_web"]
    
    def calc_stats(method_results: List[ExperimentResult]) -> Dict:
        successful = [r for r in method_results if r.success]
        if not successful:
            return {"count": 0}
        
        stats = {
            "count": len(successful),
            "total_count": len(method_results),
            "avg_latency": sum(r.latency for r in successful) / len(successful),
            "avg_cost": sum(r.cost_usd for r in successful) / len(successful),
            "avg_tokens_in": sum(r.tokens_input for r in successful) / len(successful),
            "avg_tokens_out": sum(r.tokens_output for r in successful) / len(successful),
        }
        
        # Quality scores
        quality_results = [r for r in successful if r.quality]
        if quality_results:
            stats["has_quality"] = True
            stats["quality_count"] = len(quality_results)
        
        return stats
    
    statsA = calc_stats(methodA_results)
    statsB = calc_stats(methodB_results)
    
    print("\nOPTION A: HTML content → LLM (no web access)")
    print(f"  Success rate: {statsA['count']}/{statsA.get('total_count', 0)}")
    if statsA["count"] > 0:
        print(f"  Avg latency: {statsA['avg_latency']:.2f}s")
        print(f"  Avg cost: ${statsA['avg_cost']:.4f}")
        print(f"  Avg tokens: {statsA['avg_tokens_in']:.0f} in / {statsA['avg_tokens_out']:.0f} out")
        
        # Quality scores (term-grounded)
        quality_scores = []
        all_missed_terms = []
        for r in methodA_results:
            if r.success and r.quality and "term_grounded" in r.quality:
                quality_scores.append(r.quality["term_grounded"]["scores"]["overall"])
                missed = r.quality["term_grounded"].get("missed_terms", [])
                all_missed_terms.extend(missed)
        
        if quality_scores:
            avg_score = sum(quality_scores) / len(quality_scores)
            print(f"  Avg quality (term-grounded relevance): {avg_score:.1f}/10")
            if all_missed_terms:
                # Show top 3 most common missed terms
                from collections import Counter
                top_missed = Counter(all_missed_terms).most_common(3)
                if top_missed:
                    missed_str = ", ".join([f"{term} ({count}x)" for term, count in top_missed])
                    print(f"  Top missed terms: {missed_str}")
    
    print("\nOPTION B: URL → LLM (with web_search)")
    print(f"  Success rate: {statsB['count']}/{statsB.get('total_count', 0)}")
    if statsB["count"] > 0:
        print(f"  Avg latency: {statsB['avg_latency']:.2f}s")
        print(f"  Avg cost: ${statsB['avg_cost']:.4f}")
        print(f"  Avg tokens: {statsB['avg_tokens_in']:.0f} in / {statsB['avg_tokens_out']:.0f} out")
        
        # Quality scores (term-grounded)
        quality_scores = []
        all_drift_topics = []
        for r in methodB_results:
            if r.success and r.quality and "term_grounded" in r.quality:
                quality_scores.append(r.quality["term_grounded"]["scores"]["overall"])
                drift = r.quality["term_grounded"].get("drift_topics", [])
                all_drift_topics.extend(drift)
        
        if quality_scores:
            avg_score = sum(quality_scores) / len(quality_scores)
            print(f"  Avg quality (term-grounded relevance): {avg_score:.1f}/10")
            if all_drift_topics:
                # Show top 3 most common drift topics
                from collections import Counter
                top_drift = Counter(all_drift_topics).most_common(3)
                if top_drift:
                    drift_str = ", ".join([f"{topic} ({count}x)" for topic, count in top_drift])
                    print(f"  Drift topics: {drift_str}")
    
    # Winner analysis
    print("\n" + "-" * 80)
    print("ANALYSIS:")
    if statsA["count"] > 0 and statsB["count"] > 0:
        # Latency
        if statsA["avg_latency"] < statsB["avg_latency"]:
            delta = ((statsB["avg_latency"] / statsA["avg_latency"]) - 1) * 100
            print(f"  🏆 LATENCY: Option A is {delta:.0f}% faster")
        else:
            delta = ((statsA["avg_latency"] / statsB["avg_latency"]) - 1) * 100
            print(f"  🏆 LATENCY: Option B is {delta:.0f}% faster")
        
        # Cost
        if statsA["avg_cost"] < statsB["avg_cost"]:
            delta = ((statsB["avg_cost"] / statsA["avg_cost"]) - 1) * 100
            print(f"  💰 COST: Option A is {delta:.0f}% cheaper")
        else:
            delta = ((statsA["avg_cost"] / statsB["avg_cost"]) - 1) * 100
            print(f"  💰 COST: Option B is {delta:.0f}% cheaper")
        
        # Quality (term-grounded relevance)
        quality_A = [r.quality["term_grounded"]["scores"]["overall"] 
                    for r in methodA_results if r.success and r.quality and "term_grounded" in r.quality]
        quality_B = [r.quality["term_grounded"]["scores"]["overall"] 
                    for r in methodB_results if r.success and r.quality and "term_grounded" in r.quality]
        
        if quality_A and quality_B:
            avg_A = sum(quality_A) / len(quality_A)
            avg_B = sum(quality_B) / len(quality_B)
            delta = avg_B - avg_A  # Positive if B is better
            if delta > 1.0:
                print(f"  ✨ QUALITY: Option B is {delta:.1f} points better (term-grounded relevance)")
            elif delta < -1.0:
                print(f"  ✨ QUALITY: Option A is {-delta:.1f} points better (term-grounded relevance)")
            else:
                print(f"  ✨ QUALITY: Similar (Δ={abs(delta):.1f})")
            
            # Additional diagnostics
            print(f"  📊 TRADE-OFF: A={avg_A:.1f}/10 (fast, cheap, grounded), B={avg_B:.1f}/10 (enriched context)")
    
    print("=" * 80)


if __name__ == "__main__":
    run_experiment()
