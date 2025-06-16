import pytest
from app.main import run_full_pipeline
from app.db.database import SessionLocal, Base, engine
from app.db.models import PipelineRun
import asyncio
from app.main import PipelineConfig
from app.pipeline_status import PipelineStatus

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
    monkeypatch.setattr('app.main.Pipeline.run_pipeline', fake_run_pipeline)
    # Run the pipeline
    config = PipelineConfig(
        model="dall-e-3",
        zazzle_template_id="test_template_id",
        zazzle_tracking_code="test_tracking_code",
        prompt_version="1.0.0"
    )
    try:
        asyncio.run(run_full_pipeline(config))
    except Exception:
        pass
    # Check that a PipelineRun was created
    session = SessionLocal()
    runs = session.query(PipelineRun).all()
    assert len(runs) == 1
    run = runs[0]
    assert run.status in {status.value for status in PipelineStatus}
    assert run.start_time is not None
    assert run.end_time is not None
    session.close() 