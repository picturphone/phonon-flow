"""Command-line interface for PhononFlow."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from phonon_flow import __version__
from phonon_flow.config import PhononConfig
from phonon_flow.phonon.workflow import PhononWorkflow
from phonon_flow.backends import create_backend

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="phonon-flow")
def main():
    """PhononFlow — Remote-first first-principles phonon calculation workflow.

    Automates VASP + phonopy calculations on Raspberry Pi, HPC clusters,
    or local machines, with IMA knowledge base integration.
    """
    pass


@main.command()
@click.option("-c", "--config", "config_path", default="phonon_config.yaml",
              help="Path to YAML configuration file.")
@click.option("-s", "--step", "steps", multiple=True,
              type=click.Choice(["relax", "displace", "forces", "bands", "raman", "plot", "report", "sync"]),
              help="Specific step(s) to run (can be specified multiple times).")
@click.option("--skip", "skip_steps", multiple=True,
              type=click.Choice(["relax", "displace", "forces", "bands", "raman", "plot", "report", "sync"]),
              help="Step(s) to skip.")
@click.option("--backend", "backend_type", default=None,
              type=click.Choice(["hpc_slurm", "local"]),
              help="Override backend type.")
def run(config_path: str, steps: tuple, skip_steps: tuple, backend_type: Optional[str]):
    """Run the phonon calculation workflow.

    Examples:

    \b
    # Run the full pipeline
    phonon-flow run -c si_phonon.yaml

    \b
    # Run only specific steps
    phonon-flow run -c si_phonon.yaml -s relax -s displace

    \b
    # Skip knowledge sync
    phonon-flow run -c si_phonon.yaml --skip sync
    """
    config = PhononConfig.from_yaml(config_path)

    if backend_type:
        config.backend.type = backend_type

    wf = PhononWorkflow(config)

    if steps:
        step_map = {
            "relax": wf.run_relax,
            "displace": wf.run_displace,
            "forces": wf.run_forces,
            "bands": wf.run_bands,
            "raman": wf.run_raman,
            "plot": wf.run_plot,
            "report": wf.render_report,
            "sync": wf.sync_knowledge,
        }
        try:
            for step_name in steps:
                console.print(f"\n[bold]Running step: {step_name}[/bold]")
                step_map[step_name]()
        finally:
            wf.disconnect()
    else:
        wf.run_all(skip=list(skip_steps))


@main.command()
@click.option("-c", "--config", "config_path", default="phonon_config.yaml",
              help="Path to YAML configuration file.")
def check(config_path: str):
    """Verify configuration and backend connectivity.

    Checks:
    - Config validity
    - Backend connection
    - VASP availability
    - POTCAR elements
    """
    console.print(f"[cyan]Checking config: {config_path}[/cyan]\n")

    config = PhononConfig.from_yaml(config_path)

    # Check config basics
    console.print(f"  Material:   {config.material.name}")
    console.print(f"  Elements:   {', '.join(config.material.potcar_elements)}")
    console.print(f"  Crystal:    {config.material.crystal_system}")
    console.print(f"  Space Group: {config.material.space_group}")
    console.print(f"  Backend:     {config.backend.type}")
    console.print(f"  Supercell:   {config.phonopy.supercell_dim}")

    # Check backend
    backend = create_backend(config)

    try:
        backend.connect()

        if config.backend.type == "hpc_slurm":
            out, _ = backend.run_command("hostname && squeue -u $USER 2>/dev/null | head -5")
            console.print(f"\n  [green]HPC connected: {out.strip()}[/green]")

            elements = backend.get_potcar_elements()
            missing = [e for e in config.material.potcar_elements if e not in elements]
            if missing:
                console.print(f"  [yellow]Missing POTCAR: {', '.join(missing)}[/yellow]")
            else:
                console.print(f"  [green]POTCAR elements: all available ✓[/green]")

        elif config.backend.type == "hpc_slurm":
            out, _ = backend.run_command("hostname")
            console.print(f"\n  [green]HPC connected: {out.strip()}[/green]")

            queue = backend.list_queue()
            console.print(f"  Queue:\n{queue}")

            vasp_ok = backend.verify_environment()
            status = "[green]Deployed[/green]" if vasp_ok else "[yellow]Not verified[/yellow]"
            console.print(f"  VASP: {status} ({backend.vasp_bin})")

        console.print("\n[bold green]All checks passed ✓[/bold green]")

    except Exception as e:
        console.print(f"\n[red]Check failed: {e}[/red]")
        sys.exit(1)
    finally:
        backend.disconnect()


@main.command()
@click.argument("name")
@click.option("-e", "--elements", required=True,
              help="Comma-separated element symbols (e.g. 'Mn,P').")
@click.option("--crystal", default="orthorhombic",
              help="Crystal system (cubic, orthorhombic, hexagonal, etc.).")
@click.option("--space-group", type=int, default=62,
              help="International space group number.")
@click.option("--backend", default="hpc_slurm",
              type=click.Choice(["hpc_slurm", "local"]),
              help="Compute backend.")
@click.option("--supercell", default="2,2,2",
              help="Supercell dimensions (nx,ny,nz).")
@click.option("--magnetic/--no-magnetic", default=False,
              help="Enable spin-polarized calculation.")
@click.option("-o", "--output", default="phonon_config.yaml",
              help="Output YAML path.")
def init(name: str, elements: str, crystal: str, space_group: int,
         backend: str, supercell: str, magnetic: bool, output: str):
    """Generate a phonon calculation configuration template.

    Example:
        phonon-flow init Si -e Si --crystal cubic --space-group 227
    """
    sc = tuple(int(x) for x in supercell.split(","))

    data = {
        "material": {
            "name": name,
            "potcar_elements": [e.strip() for e in elements.split(",")],
            "crystal_system": crystal,
            "space_group": space_group,
        },
        "backend": {
            "type": backend,
        },
        "phonopy": {
            "supercell_dim": list(sc),
            "band_points": 101,
        },
        "relax_kpoints": {"grid": [8, 8, 8], "method": "Gamma"},
        "phonon_kpoints": {"grid": [6, 6, 6], "method": "Gamma"},
        "output_dir": f"./{name}_phonon_calc",
    }

    if magnetic:
        data["material"]["magnetic"] = {"enabled": True, "magmom": []}
        data["relax_settings"] = {"ispin": 2}

    # Add backend-specific templates
    if backend == "hpc_slurm":
        data["backend"]["hpc_slurm"] = {
            "host": "login.example.com",
            "port": 22,
            "username": "YOUR_USERNAME",
            "keyfile": "~/.ssh/id_rsa",
            "partition": "YOUR_PARTITION",
            "nodes": 1,
            "ntasks_per_node": 32,
            "env_setup": [
                "module purge",
                "source ~/path/to/vasp/env.sh",
            ],
            "env_exports": {
                "I_MPI_PIN_DOMAIN": "numa",
                "OMP_NUM_THREADS": "1",
            },
            "srun_cmd": "srun --mpi=pmi2 vasp_std",
        }
    elif backend == "local":
        data["backend"]["type"] = "local"

    import yaml
    with open(output, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    console.print(f"\n[green]Config template written to: {output}[/green]")
    console.print("[yellow]Edit this file with your actual paths, credentials, etc.[/yellow]")


@main.command()
@click.option("-c", "--config", "config_path", default="phonon_config.yaml",
              help="Path to YAML configuration file.")
@click.option("-j", "--json", "as_json", is_flag=True,
              help="Output as JSON instead of Markdown table.")
def status(config_path: str, as_json: bool):
    """Show calculation status and queue."""
    config = PhononConfig.from_yaml(config_path)
    backend = create_backend(config)

    try:
        backend.connect()

        if config.backend.type == "hpc_slurm":
            out = backend.list_queue()
            console.print(f"[bold]SLURM Queue:[/bold]\n{out}")

            # Check for running phonon jobs
            console.print(f"\n[bold]Phonon jobs:[/bold]")
            out, _ = backend.run_command(
                f"ls -d {backend.expand_work_dir(config.material.name)}/phonon/disp-*/vasprun.xml 2>/dev/null | wc -l"
            )
            console.print(f"  Completed displacements: {out.strip()}")

        elif config.backend.type == "hpc_slurm":
            out, _ = backend.run_command("squeue -u $USER 2>/dev/null || echo 'No jobs running'")
            console.print(f"[bold]SLURM Queue:[/bold]\n{out}")

        backend.disconnect()

    except Exception as e:
        console.print(f"[red]Status check failed: {e}[/red]")


@main.command()
@click.option("-c", "--config", "config_path", default="phonon_config.yaml",
              help="Path to YAML configuration file.")
@click.option("--kill", is_flag=True, help="Kill all jobs for the current user.")
def queue(config_path: str, kill: bool):
    """Manage SLURM job queue.

    \b
    phonon-flow queue -c config.yaml        # List jobs
    phonon-flow queue -c config.yaml --kill # Cancel all jobs
    """
    config = PhononConfig.from_yaml(config_path)

    if config.backend.type != "hpc_slurm":
        console.print("[yellow]Queue management only available for HPC SLURM backend[/yellow]")
        return

    backend = create_backend(config)
    backend.connect()

    try:
        if kill:
            backend.delete_queue_all()
            console.print("[green]All jobs canceled ✓[/green]")
        else:
            out = backend.list_queue()
            console.print(f"[bold]SLURM Queue:[/bold]\n{out}")
    finally:
        backend.disconnect()


if __name__ == "__main__":
    main()
