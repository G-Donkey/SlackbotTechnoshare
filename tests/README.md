# TechnoShare Commentator: Testing Guide

This guide explains **why** we test, **how** we test, and **what** specific parts of the system are being verified. It is written for project managers, stakeholders, and anyone interested in ensuring the reliability of the bot.

---

## 🏗 Why do we use "Pytest"?

We use a tool called **Pytest** to run our tests. Think of Pytest as a "quality control robot" that checks our work. It works well because:

1.  **It finds bugs automatically**: Instead of a human clicking around manually for hours, Pytest runs hundreds of checks in seconds.
2.  **It reads like plain English**: Even if you don't code, the test results show clear "Pass" or "Fail" signals.
3.  **It scales**: We can start with 10 tests and grow to 10,000 without changing how we run them.

---

## 🧰 What are "Fixtures"?

You will see the word "feature" or "fixture" often. In testing, a **fixture** is like setting the table before dinner.

-   **Why use them?** If every test had to "create a database," "login to Slack," and "load configuration" from scratch, the code would be messy and slow.
-   **How they help**: A fixture does the setup **once** (e.g., "Create a temporary database") and hands it to any test that needs it. This keeps tests clean and focused on *testing*, not *preparing*.

---

## 🌓 The Two Types of Tests

We split our tests into two camps: **Unit** and **Integration**.

### 1. Unit Tests (The "Fast Check")
*Located in `tests/unit/`*

These tests checks individual components in isolation. Think of testing a car part: "Does this spark plug spark?" We don't need to build the whole car to know if the plug works.

-   **Why they matter**: They run instantly (milliseconds). We run them every time we save a file to catch typos and logic errors immediately.
-   **What is "Mocking"?**: Since these tests are isolated, we fake external things. We don't actually call OpenAI or Slack; we just pretend to. This guarantees the test never fails because the internet is down.

**Key Unit Tests:**
-   `test_llm_logic.py`: "If we give the AI this text, does it build the correct prompt?" (No API cost).
-   `test_slack_client.py`: "Does our code format messages correctly for Slack?"
-   `test_url_extract.py`: "Can we find a link buried in a long message?"
-   `test_idempotency.py`: "Do we correctly ignore messages we've already processed?" (Prevents bot spam loops).

### 2. Integration Tests (The "Real Deal")
*Located in `tests/integration/`*

These tests verify that different parts work *together* and often talk to the real world. Think of a test drive: "Does the car actually drive on the road?"

-   **Why they matter**: Sometimes the code is perfect, but the password is wrong, or the API changed. These tests catch "reality" bugs.
-   **The Cost**: They are slower and cost money (OpenAI tokens), so we run them less often (e.g., before a final release).

**Key Integration Tests:**
-   `test_real_llm_search.py`: **The Big One.** We give the bot a real link (e.g., a Meta AI blog post) and ask it to use its "Search Tool" to read it and summarize it using the *actual* OpenAI API. This proves the bot really "understands" the web.
-   `test_slack_integration.py`: We actually send a message to a private Slack channel to verify our bot token works and we can post threads.

---

## 🚦 How to Run Them

If you are a developer, here is your cheat sheet:

1.  **Fast / Safe (Unit)**:
    ```bash
    uv run pytest tests/unit
    ```
    *Runs in < 1 second. Safe to run constantly.*

2.  **Real / Slow (Integration)**:
    ```bash
    RUN_INTEGRATION_TESTS=1 uv run pytest tests/integration
    ```
    *Requires `OPENAI_API_KEY` and `SLACK_BOT_TOKEN`. Costs money.*

---
