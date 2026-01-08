from technoshare_commentator.llm.stage_b_schema import StageBResult
from technoshare_commentator.rendering.slack_format import render_stage_b_to_markdown, render_stage_b_to_slack


def test_two_blank_lines_between_sections():
    r = StageBResult(
        tldr=["A sentence.", "Another sentence.", "Third sentence."],
        summary=[f"Sentence {i}." for i in range(10)],
        projects=["**General** — Do something." for _ in range(3)],
        similar_tech=[],
    )
    md = render_stage_b_to_markdown(r)
    # Two blank lines means 3 newlines between blocks
    assert "\n\n\n**Summary**" in md
    assert "\n\n\n**Projects**" in md
    assert "\n\n\n**Similar tech**" in md
    # confidence removed from output


def test_bold_conversion_markdown_to_slack():
    r = StageBResult(
        tldr=["Use **bold** here.", "Another **term** here.", "Final **bit** here."],
        summary=[f"Has **x{i}**." for i in range(10)],
        projects=["**LLMOps** — Test **bold** conversion." for _ in range(3)],
        similar_tech=["**TechX** — Fast."],
    )
    slack = render_stage_b_to_slack(r)
    assert "**" not in slack
    assert "*bold*" in slack
    assert "*LLMOps*" in slack  # Theme names should be converted to *bold*
