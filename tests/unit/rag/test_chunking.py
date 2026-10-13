"""Unit tests for job description chunking and section extraction."""
from ai.rag.chunking.job_description_chunker import JobDescriptionChunker


def test_chunker_clean_text():
    chunker = JobDescriptionChunker()
    html = "<p>Join our team! <b>Build models</b> with PyTorch.</p>"
    clean = chunker.clean_text(html)
    assert clean == "Join our team! Build models with PyTorch."
    assert chunker.clean_text(None) == ""


def test_chunker_section_detection():
    chunker = JobDescriptionChunker(chunk_size=300, overlap=50)
    desc = """
    About Us: We are a top AI lab building foundation models.
    Responsibilities: What you will do: Lead model training pipelines and optimize GPU clusters.
    Requirements: Qualifications: 5+ years with PyTorch, distributed training, and CUDA.
    Compensation: Salary range is $180,000 to $240,000 with generous equity.
    """
    chunks = chunker.chunk_job(
        job_id="job_123",
        title="Senior AI Researcher",
        description=desc,
        company="Acme AI",
    )

    assert len(chunks) >= 2
    # First chunk is the header
    assert chunks[0].section_name == "header"
    assert chunks[0].content == "Senior AI Researcher at Acme AI"

    # Subsequent chunks should have metadata and section detection
    sections = [c.section_name for c in chunks]
    assert any(s in ("about", "responsibilities", "requirements", "benefits") for s in sections)


def test_chunker_empty_input():
    chunker = JobDescriptionChunker()
    assert chunker.chunk_job("job_1", "Title", "") == []
