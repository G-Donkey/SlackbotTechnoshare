# Experiment Results

This folder contains JSON output files from experiments.

## File Naming Convention

`extraction_comparison_YYYYMMDD_HHMMSS.json`

## Structure

Each JSON file contains:
```json
{
  "timestamp": "20260120_143022",
  "test_urls": ["url1", "url2", ...],
  "results": [
    {
      "url": "https://example.com",
      "method": "our_approach",
      "success": true,
      "latency_seconds": 4.23,
      "tokens_input": 1500,
      "tokens_output": 420,
      "cost_usd": 0.0079,
      "output": {...}
    },
    ...
  ]
}
```

## Latest Experiment Results (2026-01-20)

### Test Configuration
- **URLs tested**: 4 diverse sources (Ars Technica news, GitHub repo, arXiv paper, Amazon blog)
- **Method A**: HTML extraction → LLM analysis (no web access)
- **Method B**: URL → LLM with web_search tool (OpenAI Responses API)
- **Evaluation metric**: Term-grounded relevance (does output address key page terms correctly and helpfully?)

### Results Summary

| Metric | Option A (HTML) | Option B (web_search) | Winner |
|--------|-----------------|----------------------|--------|
| **Success Rate** | 4/4 (100%) | 4/4 (100%) | Tie |
| **Avg Latency** | 17.75s | 26.83s | **A (51% faster)** |
| **Avg Cost** | $0.0119 | $0.0580 | **A (387% cheaper)** |
| **Avg Tokens** | 1,133 in / 908 out | 17,418 in / 1,442 out | A (15x less input) |
| **Quality Score** | 7.8/10 | 6.8/10 | **A (1.0 point better)** |

### Quality Analysis

**Option A strengths:**
- Consistently high scores (7-9/10 across all URLs)
- Focused on page content, minimal drift
- Only missed minor details (author names: Fidji Simo, Adam Fry; source attribution: Wired)

**Option B weaknesses:**
- Lower average quality despite web access (6-8/10)
- Exhibited drift to off-topic content:
  - Meta/Instagram ad model comparisons (not on target page)
  - Microsoft Copilot / Google Gemini monetization (irrelevant to OpenAI article)
  - Amazon retail media framing (generic business model discussion)
- Used 20+ web sources but didn't improve term coverage

### Individual URL Results

1. **Ars Technica** (OpenAI ads): A=8/10, B=6/10 (A wins by 2 points)
2. **GitHub repo** (SAM 3D): A=7/10, B=6/10 (A wins by 1 point)
3. **arXiv paper**: A=9/10, B=8/10 (A wins by 1 point)
4. **Amazon blog**: A=7/10, B=7/10 (tie)

## Conclusion

**Option A (HTML extraction → LLM) is the clear winner across all dimensions:**

✅ **Performance**: 51% faster (18s vs 27s average)  
✅ **Cost Efficiency**: ~5x cheaper ($0.012 vs $0.058 per analysis)  
✅ **Quality**: Better term-grounded relevance (7.8/10 vs 6.8/10)  
✅ **Focus**: Stays on-topic, minimal drift to irrelevant content

**Why Option B (web_search) underperforms:**
- Web access doesn't improve understanding of what's on the page
- Adds latency fetching external sources (20+ sources per request)
- Increases token usage 15x without quality benefit
- Introduces drift: discusses competitors, alternative business models, generic industry trends

**Architectural validation:**
This experiment confirms that **manually extracting and curating page content** before LLM analysis provides:
1. Better cost efficiency (5x cheaper)
2. Better performance (51% faster)
3. Better quality (1.0 point higher)
4. Better observability (you control exactly what the LLM sees)

The "web_search enrichment" hypothesis is **rejected**: giving the LLM web access for analyzing specific pages adds cost and latency without improving term coverage or correctness, while introducing unwanted drift to tangential topics.

## Analysis Scripts

To analyze results programmatically:
```python
import json
from pathlib import Path

# Load latest result
results_dir = Path("experiments/results")
latest = sorted(results_dir.glob("*.json"))[-1]

with open(latest) as f:
    data = json.load(f)

# Compare methods
for result in data["results"]:
    print(f"{result['method']}: {result['latency_seconds']}s, ${result['cost_usd']}")
    if result.get('quality'):
        print(f"  Quality: {result['quality']['term_grounded']['scores']['overall']}/10")
```
