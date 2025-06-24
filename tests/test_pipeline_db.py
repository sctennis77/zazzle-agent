import asyncio

import pytest

from app.db.database import Base, SessionLocal, engine
from app.db.models import PipelineRun
from app.main import PipelineConfig, run_full_pipeline
from app.pipeline_status import PipelineStatus
from app.image_generator import IMAGE_GENERATION_BASE_PROMPTS


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Drop and recreate all tables before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
def test_pipeline_run_creates_pipelinerun(monkeypatch):
    # Patch pipeline to simulate an error (no products generated)
    async def fake_run_pipeline(self):
        raise Exception("No products were generated. pipeline_run_id: 1")

    monkeypatch.setattr("app.main.Pipeline.run_pipeline", fake_run_pipeline)
    # Run the pipeline
    config = PipelineConfig(
        model="dall-e-3",
        zazzle_template_id="test_template_id",
        zazzle_tracking_code="test_tracking_code",
        prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
    )
    try:
        asyncio.run(run_full_pipeline(config))
    except Exception:
        pass
    # Check that PipelineRuns were created (one for each subreddit attempt)
    session = SessionLocal()
    runs = session.query(PipelineRun).all()
    # With subreddit cycling, we expect 5 pipeline runs (max_subreddit_attempts)
    assert len(runs) == 5
    # Check that all runs have valid status and start_time
    for run in runs:
        assert run.status in {status.value for status in PipelineStatus}
        assert run.start_time is not None
        # Note: end_time may not be set for failed runs
    session.close()
