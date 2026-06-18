"""CLI for ShopWorld - command-line interface for running scenarios."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(
    name="shopworld",
    help="ShopWorld: A deterministic RL environment for Shopify merchant AI agents",
    add_completion=False,
)
console = Console()


@app.command()
def version():
    """Show ShopWorld version."""
    from shopworld import __version__
    console.print(f"ShopWorld {__version__}")


@app.command()
def hello():
    """Run hello world example."""
    from shopworld.examples.hello_world import main
    main()


@app.command()
def test(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    path: Optional[Path] = typer.Option(None, "--path", help="Test path to run"),
):
    """Run test suite."""
    import pytest
    
    args = ["-v"] if verbose else []
    if path:
        args.append(str(path))
    else:
        args.append("tests/")
    
    sys.exit(pytest.main(args))


@app.command()
def schema(
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file"),
):
    """Show database schema."""
    from sqlmodel import SQLModel
    
    # Create schema table
    table = Table(title="ShopWorld Database Schema")
    table.add_column("Table", style="cyan")
    table.add_column("Columns", style="green")
    
    for mapper in SQLModel.metadata.mappers:
        if hasattr(mapper, "local_table"):
            name = mapper.local_table.name
            columns = [c.name for c in mapper.local_table.columns]
            table.add_row(name, ", ".join(columns[:5]) + ("..." if len(columns) > 5 else ""))
    
    console.print(table)
    
    if output:
        # Write DDL to file
        from sqlalchemy import create_engine
        engine = create_engine("sqlite:///:memory:")
        with open(output, "w") as f:
            for line in SQLModel.metadata.create_all(engine, checkfirst=False):
                if line:
                    f.write(str(line) + ";\n")
        console.print(f"\nSchema written to {output}")


@app.command()
def run(
    task: str = typer.Argument(..., help="Task ID to run"),
    seed: int = typer.Option(42, "-s", "--seed", help="Random seed"),
    steps: int = typer.Option(100, "-n", "--steps", help="Max steps"),
    agent: str = typer.Option("dummy", "-a", "--agent", help="Agent type (dummy, react, function)"),
):
    """Run a single task episode."""
    console.print(Panel(f"Running task: {task}", title="ShopWorld", border_style="blue"))
    
    from shopworld.environment import ShopWorldEnv, Action
    from shopworld.task import TaskLoader
    
    # Load task
    loader = TaskLoader()
    loader.load_all()
    task_obj = loader.get_task(task)
    
    if not task_obj:
        console.print(f"[red]Task not found: {task}[/red]")
        raise typer.Exit(1)
    
    # Create environment
    env = ShopWorldEnv(task=task_obj, max_steps=steps)
    obs, info = env.reset(seed=seed)
    
    console.print(f"Episode: {info['episode_id']}")
    console.print(f"Granted scopes: {info['granted_scopes']}")
    
    # Simple dummy agent for now
    done = False
    step_count = 0
    
    while not done:
        # Dummy action - query orders
        action = Action(tool_name="query_orders", arguments={"limit": 10})
        obs, reward, terminated, truncated, info = env.step(action)
        
        done = terminated or truncated
        step_count += 1
        
        if step_count % 10 == 0:
            console.print(f"Step {step_count}...")
    
    # Evaluate
    result = env.evaluate()
    console.print(f"\n[green]Episode complete after {step_count} steps[/green]")
    console.print(f"Task success: {result.get('task_completion', {}).get('success', False)}")


def main():
    """Entry point for shopworld CLI."""
    app()


if __name__ == "__main__":
    main()
