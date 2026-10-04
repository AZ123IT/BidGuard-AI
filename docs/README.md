# BidGuard AI Documentation

[Project overview (English)](../README.en.md) · [中文项目介绍](../README.md)

## Start Here

| Guide | What you will find |
| --- | --- |
| [Demo walkthrough](demo_walkthrough.md) | Run the application, inspect evidence, review risks, compare contracts, and verify the project |
| [Interview brief](interview_brief.md) | Project pitch, engineering decisions, limitations, and interview questions |
| [Release notes](release_notes_v0_1.md) | Included features and release scope |

## Understand The Implementation

| Guide | What you will find |
| --- | --- |
| [Architecture](architecture.md) | Component boundaries, ingestion, retrieval, and provider abstractions |
| [Database design](database_design.md) | Models, migrations, SQLite fallback, and PostgreSQL/pgvector setup |
| [Agent workflow](agent_workflow.md) | Rule-based routing, evidence checks, tools, and trace behavior |

## Examine The Evidence

| Guide | What you will find |
| --- | --- |
| [Evaluation design](evaluation_plan.md) | Workflow coverage, retrieval metrics, provider observations, and commands |
| [Failure analysis](evaluation_failure_analysis.md) | Historical baseline comparisons, failed cases, and limits of the small synthetic dataset |
| [Real-provider demo](real_provider_demo.md) | Optional Ollama/DeepSeek setup and the recorded pgvector experiment |
| [Roadmap](development_roadmap.md) | Remaining work and intentionally excluded features |

## Chinese Learning Resources

- [System learning guide](system_learning_cn.md): data flow, retrieval calculations, evidence checks, tool workflow, and a hands-on API exercise.
- [Interview question bank](interview_qa_cn.md): detailed questions and answers for technical follow-up practice.

Recorded experiment results are historical measurements. Use the verification commands to check your current environment; workflow pass rates are not production answer-accuracy guarantees.
