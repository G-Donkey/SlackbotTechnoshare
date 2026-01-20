from technoshare_commentator.llm.schema import AnalysisResult
from technoshare_commentator.rendering.slack_format import render_analysis_to_markdown, render_analysis_to_slack


def test_two_blank_lines_between_sections():
    r = AnalysisResult(
        tldr=["A sentence.", "Another sentence.", "Third sentence."],
        summary="This is a summary paragraph with multiple sentences. It covers the key points of the content. The technology offers significant benefits. Performance benchmarks show improvements. Overall it represents a step forward.",
        projects=["**General** — Do something." for _ in range(3)],
        similar_tech=[],
    )
    md = render_analysis_to_markdown(r)
    # Two blank lines means 3 newlines between blocks
    assert "\n\n\n**Summary**" in md
    assert "\n\n\n**Projects**" in md
    assert "\n\n\n**Similar tech**" in md


def test_bold_conversion_markdown_to_slack():
    r = AnalysisResult(
        tldr=["Use **bold** here.", "Another **term** here.", "Final **bit** here."],
        summary="This has **bold** terms in the summary paragraph. Multiple **key** words are highlighted. The content covers **important** technical details that are worth noting.",
        projects=["**LLMOps** — Test **bold** conversion." for _ in range(3)],
        similar_tech=["**TechX** — Fast."],
    )
    slack = render_analysis_to_slack(r)
    assert "**" not in slack
    assert "*bold*" in slack
    assert "*LLMOps*" in slack  # Theme names should be converted to *bold*
