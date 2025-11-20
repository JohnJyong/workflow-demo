import asyncio
from sqlmodel import Session, select
from workflow.models import WorkflowDefinition, NodeConfig
from workflow.engine import WorkflowEngine
from workflow.database import create_db_and_tables, engine, Workflow, WorkflowRun, get_session

async def main():
    # 1. Initialize DB
    create_db_and_tables()
    
    # 2. Define and Save Workflow
    nodes = [
        NodeConfig(id="start", type="start", next_nodes=["end"], params={"foo": "bar"}),
        NodeConfig(id="end", type="end")
    ]
    definition = WorkflowDefinition(nodes=nodes)
    
    with Session(engine) as session:
        wf = Workflow(name="test_workflow", definition=definition.model_dump())
        session.add(wf)
        session.commit()
        session.refresh(wf)
        print(f"Saved Workflow ID: {wf.id}")
        workflow_id = wf.id

    # 3. Run Workflow with Persistence
    # Re-instantiate engine from saved definition (simulating loading)
    with Session(engine) as session:
        wf = session.get(Workflow, workflow_id)
        loaded_def = WorkflowDefinition(**wf.definition)
    
    engine_instance = WorkflowEngine(loaded_def)
    print("Running workflow...")
    await engine_instance.run(workflow_id=workflow_id, session_factory=get_session)
    
    # 4. Verify Run Record
    with Session(engine) as session:
        statement = select(WorkflowRun).where(WorkflowRun.workflow_id == workflow_id)
        runs = session.exec(statement).all()
        
        print(f"\nFound {len(runs)} run(s).")
        for run in runs:
            print(f"Run ID: {run.id}, Status: {run.status}, Results: {run.results}")
            if run.status == "completed" and run.results:
                print("SUCCESS: Run recorded correctly.")
            else:
                print("FAILURE: Run record missing or incorrect.")

if __name__ == "__main__":
    asyncio.run(main())
