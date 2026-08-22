"""Agent-graph wiring: the whole tree constructs and has the right shape."""

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent

from bookforge.agents.orchestrator import (
    BookProductionAgent,
    build_chapter_pipeline,
    build_root_agent,
)
from bookforge.config import get_settings


def test_root_graph_shape():
    root = build_root_agent(get_settings())
    assert isinstance(root, SequentialAgent)
    names = [a.name for a in root.sub_agents]
    assert names == ["channel_intake", "book_production", "book_compiler"]


def test_chapter_pipeline_shape():
    pipeline = build_chapter_pipeline(get_settings())
    names = [a.name for a in pipeline.sub_agents]
    assert names == [
        "media_acquisition",
        "transcript_analyst",
        "visual_assets",
        "chapter_writer",
        "chapter_qa_loop",
    ]
    qa = pipeline.sub_agents[-1]
    assert isinstance(qa, LoopAgent)
    assert qa.max_iterations == get_settings().qa_max_iterations
    assert [a.name for a in qa.sub_agents] == ["chapter_critic", "chapter_refiner"]


def test_llm_agents_are_leaf_workers():
    pipeline = build_chapter_pipeline(get_settings())
    llms = [a for a in pipeline.sub_agents if isinstance(a, LlmAgent)]
    for agent in llms + list(pipeline.sub_agents[-1].sub_agents):
        assert isinstance(agent, LlmAgent)
        assert agent.disallow_transfer_to_parent is True
        assert not agent.sub_agents  # no transfer targets


def test_production_agent_registers_pipeline_as_subagent():
    pipeline = build_chapter_pipeline(get_settings())
    production = BookProductionAgent(pipeline=pipeline)
    assert production.pipeline is pipeline
    assert production.sub_agents == [pipeline]


def test_analyst_uses_structured_output():
    pipeline = build_chapter_pipeline(get_settings())
    analyst = pipeline.sub_agents[1]
    assert isinstance(analyst, LlmAgent)
    assert analyst.output_schema is not None
    assert analyst.output_key == "analysis_json"
    assert not analyst.tools  # output_schema forbids tools; analyst has none
