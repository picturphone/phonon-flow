"""
Core phonon calculation workflow engine.

End-to-end automation of:
  📐 Structure relaxation (relax)
  🔀 Supercell displacement generation (displace)
  ⚡ Force constant calculation (forces)
  📊 Phonon band structure analysis (bands)
  🔬 Raman activity classification (raman)
  🎨 Publication-ready visualization (plot)
  📚 IMA knowledge base sync (sync)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from phonon_flow.backends import RemoteBackend, create_backend, HPCSLURMBackend
from phonon_flow.config import PhononConfig
from phonon_flow.constants import (
    BAND_PATHS,
    CM1_TO_THZ,
    THZ_TO_CM1,
)
from phonon_flow.exceptions import (
    PhonopyError,
    ValidationError,
    VASPError,
    VASPNotConvergedError,
    BackendError,
)
from phonon_flow.phonon.templates import (
    generate_band_conf,
    generate_incar_phonon,
    generate_incar_relax,
    generate_kpoints,
)
from phonon_flow.phonon.bands import (
    check_stability,
    extract_frequencies,
    get_band_structure_summary,
    load_band_yaml,
)
from phonon_flow.phonon.raman import (
    classify_raman_modes,
    format_mode_table,
    get_raman_active_modes,
    parse_irreps_output,
)

console = Console()


class PhononWorkflow:
    """Main phonon calculation workflow orchestrator.

    Manages the entire pipeline from raw structure to publication-ready
    phonon dispersion and Raman analysis, with support for:
    - Local execution (phonopy post-processing)
    - HPC SLURM clusters (production VASP)
    - IMA knowledge base archival

    Example:
        >>> config = PhononConfig.from_yaml("si_phonon.yaml")
        >>> wf = PhononWorkflow(config)
        >>> wf.run_relax()       # Step 1
        >>> wf.run_displace()    # Step 2
        >>> wf.run_forces()      # Step 3
        >>> wf.run_bands()       # Step 4
        >>> wf.run_raman()       # Step 5
        >>> wf.render_report()   # Generate summary
        >>> wf.sync_knowledge()  # Upload to IMA
    """

    # Workflow step definitions
    STEPS = [
        ("relax", "Structure Relaxation", "🔧"),
        ("displace", "Supercell Displacements", "🔀"),
        ("forces", "Force Calculations", "⚡"),
        ("bands", "Phonon Band Structure", "📊"),
        ("raman", "Raman Activity Analysis", "🔬"),
        ("plot", "Visualization", "🎨"),
        ("report", "Summary Report", "📋"),
        ("sync", "Knowledge Sync", "📚"),
    ]

    def __init__(self, config: PhononConfig, backend: Optional[RemoteBackend] = None):
        """Initialize the workflow.

        Args:
            config: PhononFlow configuration.
            backend: Remote backend (auto-created from config if None).
        """
        self.config = config
        self.backend = backend or create_backend(config)
        self.output_dir = Path(config.output_dir)
        self._connected = False
        self._results: Dict[str, Any] = {}
        self._job_ids: List[str] = []

    # ── Connection Management ──────────────────────────────

    def connect(self) -> None:
        """Establish connection to the remote backend."""
        if not self._connected:
            console.print(f"[cyan]Connecting to {self.config.backend.type}...[/cyan]")
            self.backend.connect()
            self._connected = True
            console.print("[green]Connected ✓[/green]")

    def disconnect(self) -> None:
        """Close the connection."""
        if self._connected:
            self.backend.disconnect()
            self._connected = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    # ── Step 1: Structure Relaxation ───────────────────────

    def run_relax(self) -> Dict[str, Any]:
        """Run structure relaxation on the remote backend.

        Steps:
            1. Create remote work directory
            2. Upload POSCAR from local or generate INCAR/KPOINTS/POTCAR
            3. Generate and submit SLURM/run script
            4. Wait for completion
            5. Verify convergence
            6. Copy CONTCAR to phonon directory

        Returns:
            Dict with relaxation results (job_id, energy, lattice, etc.).
        """
        console.print("\n[bold cyan]╔══════════════════════════════════════╗")
        console.print("[bold cyan]║   Step 1: Structure Relaxation        ║")
        console.print("[bold cyan]╚══════════════════════════════════════╝[/bold cyan]\n")

        self.connect()

        material = self.config.material
        mat_name = material.name or "material"

        # Set up remote directories
        relax_dir = self.backend.expand_work_dir(f"{mat_name}/relax")
        phonon_dir = self.backend.expand_work_dir(f"{mat_name}/phonon")
        self.backend.mkdir(relax_dir)
        self.backend.mkdir(phonon_dir)

        console.print(f"  Working dir: {relax_dir}")

        # --- Upload POSCAR ---
        if material.poscar_path:
            if Path(material.poscar_path).exists():
                poscar_content = Path(material.poscar_path).read_text()
            else:
                raise FileNotFoundError(f"POSCAR not found: {material.poscar_path}")
        else:
            # Check for POSCAR in output dir
            local_poscar = self.output_dir / "POSCAR"
            if local_poscar.exists():
                poscar_content = local_poscar.read_text()
            else:
                raise FileNotFoundError(
                    "No POSCAR found. Set material.poscar_path in config "
                    "or place POSCAR in output directory."
                )

        self.backend.upload_content(poscar_content, f"{relax_dir}/POSCAR")
        console.print("  [green]POSCAR uploaded ✓[/green]")

        # --- Generate & upload INCAR ---
        rs = self.config.relax_settings
        mag = material.magnetic

        incar = generate_incar_relax(
            system=f"{mat_name} relaxation",
            encut=rs.encut,
            ediff=rs.ediff,
            ediffg=rs.ediffg,
            nsw=rs.nsw,
            ibrion=rs.ibrion,
            isif=rs.isif,
            ismear=rs.ismear,
            sigma=rs.sigma,
            prec=rs.prec,
            lwave=rs.lwave,
            lcharg=rs.lcharg,
            ispin=2 if mag and mag.enabled else None,
            magmom=mag.magmom if mag else None,
            ivdw=rs.ivdw,
            lda_plus_u=mag.lda_plus_u if mag else False,
            lda_uu=mag.lda_uu if mag else None,
            lda_ul=mag.lda_ul if mag else None,
        )
        self.backend.upload_content(incar, f"{relax_dir}/INCAR")
        console.print("  [green]INCAR generated ✓[/green]")

        # --- Generate & upload KPOINTS ---
        rk = self.config.relax_kpoints
        kpoints = generate_kpoints(method=rk.method, grid=rk.grid)
        self.backend.upload_content(kpoints, f"{relax_dir}/KPOINTS")
        console.print("  [green]KPOINTS generated ✓[/green]")

        # --- Handle POTCAR ---
        potcar_remote = f"{relax_dir}/POTCAR"
        if not self.backend.file_exists(potcar_remote):
            self._generate_potcar(potcar_remote, relax_dir)
        console.print("  [green]POTCAR ready ✓[/green]")

        # --- Generate and submit SLURM script ---
        if isinstance(self.backend, HPCSLURMBackend):
            slurm = self.backend.generate_slurm_script(
                job_name=f"{mat_name[:6]}_relax",
                work_dir=relax_dir,
            )
            # Add auto-copy CONTCAR logic
            slurm += (
                "\n# Auto-copy CONTCAR to phonon directory\n"
                "if [ -f CONTCAR ]; then\n"
                '  echo "SUCCESS: CONTCAR generated"\n'
                f"  cp CONTCAR {phonon_dir}/POSCAR\n"
                '  echo "CONTCAR copied to phonon/POSCAR"\n'
                "else\n"
                '  echo "FAILED: No CONTCAR generated"\n'
                "fi\n"
            )
            self.backend.upload_content(slurm, f"{relax_dir}/submit.slurm")
            console.print("  [yellow]Submitting SLURM job...[/yellow]")
            job_id = self.backend.submit_job(slurm, relax_dir, "submit.slurm")
            console.print(f"  [green]Job submitted: {job_id}[/green]")

        else:
            raise ValueError("Backend does not support VASP execution")

        self._job_ids.append(job_id)

        # --- Monitor ---
        console.print("  [yellow]Waiting for job to complete...[/yellow]")
        status = self.backend.wait_for_job(job_id, poll_interval=60)

        if status.state != "COMPLETED":
            raise VASPNotConvergedError(f"Relaxation failed: {status.state}")

        console.print("  [green]Relaxation completed ✓[/green]")

        # Verify convergence
        out, _ = self.backend.run_command(
            f'grep "reached required accuracy" {relax_dir}/OUTCAR | tail -1'
        )
        if "reached required accuracy" in out:
            console.print("  [green]Structure converged ✓[/green]")
        else:
            console.print("  [yellow]⚠ Convergence not detected in OUTCAR[/yellow]")

        # Extract results
        energy_out, _ = self.backend.run_command(
            f'grep "F=" {relax_dir}/OSZICAR | tail -1'
        )

        self._results["relax"] = {
            "job_id": job_id,
            "work_dir": relax_dir,
            "converged": "reached required accuracy" in out,
            "last_oszi_line": energy_out.strip(),
        }

        return self._results["relax"]

    # ── Step 2: Generate Displacements ─────────────────────

    def run_displace(self) -> Dict[str, Any]:
        """Generate supercell displacements using local phonopy.

        This step is always run locally, then displaced POSCARs are
        uploaded to the remote backend.

        Returns:
            Dict with displacement info (n_displacements, supercell_size, etc.).
        """
        console.print("\n[bold cyan]╔══════════════════════════════════════╗")
        console.print("[bold cyan]║   Step 2: Supercell Displacements     ║")
        console.print("[bold cyan]╚══════════════════════════════════════╝[/bold cyan]\n")

        material = self.config.material
        mat_name = material.name or "material"
        dim = " ".join(str(d) for d in self.config.phonopy.supercell_dim)

        # Get optimized POSCAR from relax
        if self._results.get("relax"):
            relax_dir = self._results["relax"]["work_dir"]
            self._download_if_needed(f"{relax_dir}/CONTCAR", self.output_dir / "CONTCAR_optimized")
            poscar_src = self.output_dir / "CONTCAR_optimized"
        else:
            poscar_src = Path(material.poscar_path)

        local_work = self.output_dir / "phonon"
        local_work.mkdir(parents=True, exist_ok=True)

        # Copy POSCAR
        shutil.copy(poscar_src, local_work / "POSCAR")
        os.chdir(local_work)

        # Run phonopy -d
        console.print(f"  Running: phonopy -d --dim=\"{dim}\" -c POSCAR")
        result = subprocess.run(
            ["phonopy", "-d", f"--dim={dim}", "-c", "POSCAR"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise PhonopyError(f"phonopy -d failed: {result.stderr}")

        console.print(f"  {result.stdout.strip()}")

        # Count displacement directories
        disp_dirs = sorted(local_work.glob("disp-*"))
        n_displacements = len(disp_dirs)

        # Rename to disp-001 format if needed
        for i, d in enumerate(disp_dirs, 1):
            target = local_work / f"disp-{i:03d}"
            if d.name != target.name:
                shutil.move(str(d), str(target))

        # Check for disp.yaml / phonopy_disp.yaml
        for yname in ["phonopy_disp.yaml", "disp.yaml"]:
            ypath = local_work / yname
            if ypath.exists():
                console.print(f"  [green]{yname} generated ✓[/green]")
                break

        n_atoms_super = 0
        if (local_work / "SPOSCAR").exists():
            spos = (local_work / "SPOSCAR").read_text().split("\n")
            if len(spos) > 6:
                n_atoms_super = int(spos[6].strip())

        console.print(
            f"\n  [bold green]{n_displacements} irreducible displacements[/bold green] "
            f"({n_atoms_super} atoms in supercell)"
        )

        self._results["displace"] = {
            "n_displacements": n_displacements,
            "supercell_size": n_atoms_super,
            "supercell_dim": self.config.phonopy.supercell_dim,
            "local_work_dir": str(local_work),
        }

        return self._results["displace"]

    # ── Step 3: Force Calculations ────────────────────────

    def run_forces(self, validation_first: bool = True) -> Dict[str, Any]:
        """Run phonon force calculations for all displaced configurations.

        Uses the validation-first strategy:
        1. Submit disp-001 only
        2. Verify VASP runs correctly
        3. Batch submit remaining displacements

        Args:
            validation_first: If True, validate with disp-001 before batching.

        Returns:
            Dict with force calculation results.
        """
        console.print("\n[bold cyan]╔══════════════════════════════════════╗")
        console.print("[bold cyan]║   Step 3: Force Calculations          ║")
        console.print("[bold cyan]╚══════════════════════════════════════╝[/bold cyan]\n")

        self.connect()

        material = self.config.material
        mat_name = material.name or "material"
        n_disps = self._results.get("displace", {}).get("n_displacements", 1)
        local_work = self.output_dir / "phonon"
        phonon_remote = self.backend.expand_work_dir(f"{mat_name}/phonon")

        # --- Generate phonon INCAR ---
        ps = self.config.phonon_settings
        mag = material.magnetic
        incar_phonon = generate_incar_phonon(
            system=f"{mat_name} phonon force",
            encut=ps.encut,
            ediff=ps.ediff,
            ismear=ps.ismear,
            sigma=ps.sigma,
            prec=ps.prec,
            addgrid=ps.addgrid,
            ispin=2 if mag and mag.enabled else None,
            magmom=mag.magmom if mag else None,
            lda_plus_u=mag.lda_plus_u if mag else False,
            lda_uu=mag.lda_uu if mag else None,
            lda_ul=mag.lda_ul if mag else None,
        )

        # --- Generate phonon KPOINTS ---
        pk = self.config.phonon_kpoints
        kpoints_phonon = generate_kpoints(method=pk.method, grid=pk.grid)

        # --- Prepare all displacement directories ---
        all_job_ids = []
        for i in range(1, n_disps + 1):
            disp = f"disp-{i:03d}"
            remote_disp_dir = f"{phonon_remote}/{disp}"
            self.backend.mkdir(remote_disp_dir)

            # Upload INCAR, KPOINTS
            self.backend.upload_content(incar_phonon, f"{remote_disp_dir}/INCAR")
            self.backend.upload_content(kpoints_phonon, f"{remote_disp_dir}/KPOINTS")

            # Upload displaced POSCAR
            local_disp_poscar = local_work / disp / "POSCAR"
            if local_disp_poscar.exists():
                poscar_content = local_disp_poscar.read_text()
                self.backend.upload_content(poscar_content, f"{remote_disp_dir}/POSCAR")
            else:
                # Try alternative: POSCAR-XXX format
                alt_poscar = local_work / f"POSCAR-{i:03d}"
                if alt_poscar.exists():
                    poscar_content = alt_poscar.read_text()
                    self.backend.upload_content(poscar_content, f"{remote_disp_dir}/POSCAR")
                else:
                    console.print(f"  [red]POSCAR not found for {disp}[/red]")
                    continue

            # Copy POTCAR
            potcar_src = f"{phonon_remote}/POTCAR"
            if not self.backend.file_exists(potcar_src):
                # Generate from relax POTCAR
                relax_potcar = f"{phonon_remote}/../relax/POTCAR"
                if self.backend.file_exists(relax_potcar):
                    self.backend.run_command(f"cp {relax_potcar} {phonon_remote}/POTCAR")
                else:
                    self._generate_potcar(f"{phonon_remote}/POTCAR", phonon_remote)
            self.backend.run_command(f"cp {phonon_remote}/POTCAR {remote_disp_dir}/POTCAR")

        # --- Validation-first strategy ---
        if validation_first and n_disps > 1:
            console.print("  [bold yellow]Validation phase: submitting disp-001 only[/bold yellow]")

            job_id_001 = self._submit_disp_job(phonon_remote, "001", mat_name)
            all_job_ids.append(job_id_001)
            console.print(f"  Validation job: {job_id_001}")

            # Wait a bit then check
            console.print("  Waiting 3 minutes for job to start...")
            time.sleep(180)

            # Check if VASP is iterating
            out, _ = self.backend.run_command(
                f"head -15 {phonon_remote}/disp-001/OSZICAR 2>/dev/null || echo 'not ready'"
            )
            console.print(f"  disp-001 status: {out[:200]}")

            # Wait for completion
            console.print("  Waiting for validation job...")
            status = self.backend.wait_for_job(job_id_001, poll_interval=60)

            if status.state != "COMPLETED":
                raise VASPError(f"Validation job failed: {status.state}")

            console.print("  [green]Validation passed! Submitting remaining jobs...[/green]")

            # Batch submit remaining
            for i in range(2, n_disps + 1):
                disp = f"{i:03d}"
                job_id = self._submit_disp_job(phonon_remote, disp, mat_name)
                all_job_ids.append(job_id)
                console.print(f"  disp-{disp}: {job_id}")
                time.sleep(2)

        else:
            # Submit all at once
            for i in range(1, n_disps + 1):
                disp = f"{i:03d}"
                job_id = self._submit_disp_job(phonon_remote, disp, mat_name)
                all_job_ids.append(job_id)
                console.print(f"  disp-{disp}: {job_id}")
                time.sleep(2)

        self._job_ids.extend(all_job_ids)

        # --- Wait for all ---
        console.print(f"\n  [yellow]Waiting for {len(all_job_ids)} jobs...[/yellow]")
        for jid in all_job_ids:
            status = self.backend.wait_for_job(jid, poll_interval=120)
            console.print(f"  {jid}: {status.state}")

        # --- Collect forces ---
        console.print("\n  Collecting forces → FORCE_SETS...")
        out, _ = self.backend.run_command(
            f"cd {phonon_remote} && phonopy -f disp-*/vasprun.xml 2>&1 || echo 'phonopy not on HPC'"
        )
        console.print(f"  {out.strip()}")

        # Check completion
        completed = 0
        for i in range(1, n_disps + 1):
            out, _ = self.backend.run_command(
                f"grep -c 'General timing' {phonon_remote}/disp-{i:03d}/OUTCAR 2>/dev/null || echo 0"
            )
            if out.strip() == "1":
                completed += 1

        console.print(f"\n  [bold green]Force calculations: {completed}/{n_disps} completed[/bold green]")

        self._results["forces"] = {
            "n_completed": completed,
            "n_total": n_disps,
            "job_ids": all_job_ids,
            "remote_phonon_dir": phonon_remote,
        }

        return self._results["forces"]

    # ── Step 4: Phonon Band Structure ─────────────────────

    def run_bands(self) -> Dict[str, Any]:
        """Calculate and plot phonon band structure (local).

        Downloads vasprun.xml files, collects forces, computes band structure,
        generates publication-ready plot.

        Returns:
            Dict with band structure summary.
        """
        console.print("\n[bold cyan]╔══════════════════════════════════════╗")
        console.print("[bold cyan]║   Step 4: Phonon Band Structure       ║")
        console.print("[bold cyan]╚══════════════════════════════════════╝[/bold cyan]\n")

        local_work = self.output_dir / "phonon"
        local_work.mkdir(parents=True, exist_ok=True)
        os.chdir(local_work)

        dim = " ".join(str(d) for d in self.config.phonopy.supercell_dim)

        # Step A: Collect forces
        vasprun_files = sorted(local_work.glob("disp-*/vasprun.xml"))
        if not vasprun_files:
            # Try alternative naming
            vasprun_files = sorted(Path("03_声子力计算").glob("*vasprun.xml")) if Path("03_声子力计算").exists() else []

        if vasprun_files:
            console.print(f"  Found {len(vasprun_files)} vasprun.xml files")
            cmd = ["phonopy", "-f"] + [str(f) for f in vasprun_files]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                console.print(f"  [yellow]Warning: phonopy -f: {result.stderr}[/yellow]")
            else:
                console.print("  [green]FORCE_SETS generated ✓[/green]")

        # Step B: Generate band.conf
        band_path = self.config.phonopy.band_path
        if not band_path:
            crystal = self.config.material.crystal_system
            band_path = BAND_PATHS.get(crystal, BAND_PATHS.get("Pnma", []))

        band_conf = generate_band_conf(
            material_name=" ".join(self.config.material.potcar_elements),
            dim=self.config.phonopy.supercell_dim,
            band_path=band_path or None,
            band_points=self.config.phonopy.band_points,
        )
        (local_work / "band.conf").write_text(band_conf)
        console.print("  [green]band.conf generated ✓[/green]")

        # Step C: Run phonopy band calculation
        console.print(f"  Running phonopy band calculation...")
        cmd = [
            "phonopy",
            f"--dim={dim}",  # NOTE: CLI needs = syntax
            "-c", "POSCAR",
            "-p", "band.conf",
            "-s",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise PhonopyError(f"Band calculation failed: {result.stderr}")

        console.print("  [green]Band structure calculated ✓[/green]")

        # Step D: Analyze
        band_yaml = local_work / "band.yaml"
        if band_yaml.exists():
            band_data = load_band_yaml(str(band_yaml))
            summary = get_band_structure_summary(band_data)

            console.print(f"\n  Stability: {summary['verdict']}")
            console.print(f"  Frequency range: {summary['frequency_range_thz'][1]:.2f} THz "
                          f"({summary['frequency_range_thz'][1] * THZ_TO_CM1:.0f} cm⁻¹)")
            console.print(f"  Bands: {summary['nbands']} ({summary['num_optical_modes']} optical)")

            self._results["bands"] = summary
        else:
            console.print("  [yellow]band.yaml not found, skipping analysis[/yellow]")
            self._results["bands"] = {}

        return self._results.get("bands", {})

    # ── Step 5: Raman Activity ────────────────────────────

    def run_raman(self) -> Dict[str, Any]:
        """Analyze Raman activity via Γ-point irreducible representations.

        Returns:
            Dict with Raman mode classification.
        """
        console.print("\n[bold cyan]╔══════════════════════════════════════╗")
        console.print("[bold cyan]║   Step 5: Raman Activity Analysis     ║")
        console.print("[bold cyan]╚══════════════════════════════════════╝[/bold cyan]\n")

        local_work = self.output_dir / "phonon"
        dim = " ".join(str(d) for d in self.config.phonopy.supercell_dim)
        sg = self.config.material.space_group

        if sg and sg in [11, 62, 123, 139, 166, 186, 194, 221, 225]:
            console.print(f"  Space group: {sg} (supported)")
        elif sg:
            console.print(f"  [yellow]Space group {sg}: not in built-in table, using g/u rule[/yellow]")

        # Run phonopy --irreps
        cmd = [
            "phonopy",
            f"--dim={dim}",
            "-c", "POSCAR",
            "--irreps=0 0 0",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(local_work))

        if result.returncode != 0:
            # Try alternative syntax
            result = subprocess.run(
                ["phonopy", "--dim", dim, "-c", "POSCAR", "--irreps", "0 0 0"],
                capture_output=True, text=True, cwd=str(local_work),
            )

        if result.stdout:
            modes = parse_irreps_output(result.stdout)
        else:
            console.print("  [yellow]Could not extract irreps, checking HPC...[/yellow]")
            # Try from remote
            phonon_remote = self._results.get("forces", {}).get("remote_phonon_dir", "")
            if phonon_remote:
                out, _ = self.backend.run_command(
                    f"cat {phonon_remote}/irreps_gamma.txt 2>/dev/null"
                )
                if out:
                    modes = parse_irreps_output(out)
                else:
                    modes = []
            else:
                modes = []

        if modes:
            sg_num = sg or 1
            modes = classify_raman_modes(modes, sg_num)

            raman_modes = get_raman_active_modes(modes)

            table = format_mode_table(modes)
            raman_table = format_mode_table(modes, activity_filter="raman")

            console.print(f"\n  [bold]All {len(modes)} Γ-point modes:[/bold]\n")
            console.print(table)
            console.print(f"\n  [bold green]{len(raman_modes)} Raman-active modes:[/bold green]\n")
            console.print(raman_table)

            self._results["raman"] = {
                "n_modes": len(modes),
                "n_raman": len(raman_modes),
                "raman_frequencies_cm1": [m["frequency_cm1"] for m in raman_modes],
                "raman_irreps": [m["irrep_label"] for m in raman_modes],
                "modes": modes,
                "raman_modes": raman_modes,
            }
        else:
            console.print("  [yellow]No irreps data available[/yellow]")
            self._results["raman"] = {}

        return self._results.get("raman", {})

    # ── Step 6: Visualization ─────────────────────────────

    def run_plot(self) -> None:
        """Generate publication-quality phonon band plot."""
        console.print("\n[bold cyan]╔══════════════════════════════════════╗")
        console.print("[bold cyan]║   Step 6: Visualization               ║")
        console.print("[bold cyan]╚══════════════════════════════════════╝[/bold cyan]\n")

        from phonon_flow.utils.plotting import plot_phonon_bands

        local_work = self.output_dir / "phonon"
        band_yaml = local_work / "band.yaml"

        if band_yaml.exists():
            plot_phonon_bands(
                str(band_yaml),
                output=str(local_work / "phonon_band.png"),
                title=f"{self.config.material.name} Phonon Dispersion",
                dpi=300,
            )
            console.print("  [green]Phonon band plot saved ✓[/green]")
        else:
            console.print("  [yellow]band.yaml not found, skipping plot[/yellow]")

    # ── Step 7: Report ────────────────────────────────────

    def render_report(self) -> str:
        """Generate a comprehensive Markdown report.

        Returns:
            Markdown report string.
        """
        console.print("\n[bold cyan]╔══════════════════════════════════════╗")
        console.print("[bold cyan]║   Step 7: Summary Report              ║")
        console.print("[bold cyan]╚══════════════════════════════════════╝[/bold cyan]\n")

        mat = self.config.material
        bands = self._results.get("bands", {})
        raman = self._results.get("raman", {})
        forces = self._results.get("forces", {})

        lines = [
            f"# Phonon Calculation Report: {mat.name}",
            "",
            f"**Date:** {time.strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Structure Information",
            "",
            f"- **Formula:** {mat.name}",
            f"- **Elements:** {', '.join(mat.potcar_elements)}",
            f"- **Crystal System:** {mat.crystal_system}",
            f"- **Space Group:** {mat.space_group or 'N/A'}",
        ]

        if mat.magnetic and mat.magnetic.enabled:
            lines.extend([
                f"- **Magnetic:** Spin-polarized",
                f"- **MAGMOM:** {' '.join(str(m) for m in mat.magnetic.magmom)}",
            ])

        lines.extend(["", "## Calculation Parameters", ""])
        rs = self.config.relax_settings
        ps = self.config.phonon_settings

        table_lines = [
            "| Parameter | Relax | Phonon |",
            "|-----------|-------|--------|",
            f"| ENCUT | {rs.encut} eV | {ps.encut} eV |",
            f"| EDIFF | {rs.ediff:.0e} | {ps.ediff:.0e} |",
            f"| NSW | {rs.nsw} | 0 |",
            f"| IBRION | {rs.ibrion} | -1 |",
            f"| ISMEAR | {rs.ismear} | {ps.ismear} |",
            f"| SIGMA | {rs.sigma} eV | {ps.sigma} eV |",
            f"| ADDGRID | - | {ps.addgrid} |",
        ]
        lines.extend(table_lines)

        if bands:
            lines.extend([
                "",
                "## Phonon Results",
                "",
                f"- **Stability:** {bands.get('verdict', 'N/A')}",
                f"- **Bands:** {bands.get('nbands', 'N/A')} ({bands.get('num_optical_modes', 'N/A')} optical)",
                f"- **Max Frequency:** {bands.get('max_frequency_cm1', 'N/A'):.1f} cm⁻¹" if bands.get('max_frequency_cm1') else "- **Max Frequency:** N/A",
            ])

        if raman and raman.get("raman_modes"):
            lines.extend([
                "",
                "## Raman Active Modes",
                "",
            ])
            lines.append(format_mode_table(raman["modes"], activity_filter="raman"))

        report = "\n".join(lines)
        report_path = self.output_dir / "REPORT.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        console.print(f"  [green]Report saved to {report_path}[/green]")

        self._results["report"] = report
        return report

    # ── Step 8: Knowledge Sync ────────────────────────────

    def sync_knowledge(self, kb_type: str = "report") -> bool:
        """Sync calculation results to IMA knowledge base.

        Args:
            kb_type: What to sync - 'report', 'inputs', 'all'.

        Returns:
            True if sync was successful.
        """
        console.print("\n[bold cyan]╔══════════════════════════════════════╗")
        console.print("[bold cyan]║   Step 8: Knowledge Base Sync         ║")
        console.print("[bold cyan]╚══════════════════════════════════════╝[/bold cyan]\n")

        if not self.config.knowledge or not self.config.knowledge.enabled:
            console.print("  [yellow]Knowledge base sync not enabled in config[/yellow]")
            return False

        try:
            from phonon_flow.knowledge.ima_client import IMAClient

            kb = self.config.knowledge
            client = IMAClient(client_id=kb.client_id, api_key=kb.api_key)

            mat_name = self.config.material.name or "phonon_calc"

            if kb_type in ("report", "all"):
                report = self._results.get("report", self.render_report())
                timestamp = time.strftime("%Y%m%d_%H%M")
                title = f"{mat_name}_phonon_report_{timestamp}"
                client.create_note(title=title, content=report)
                console.print(f"  [green]Report synced: {title}[/green]")

            if kb_type in ("inputs", "all"):
                # Sync configuration
                config_yaml = self.config.to_yaml(
                    self.output_dir / f"{mat_name}_config.yaml"
                )
                client.upload_file(
                    str(self.output_dir / f"{mat_name}_config.yaml"),
                    kb_id=kb.knowledge_base_id,
                )
                console.print("  [green]Config synced ✓[/green]")

            return True

        except ImportError:
            console.print("  [yellow]IMA client not available. Install with: pip install httpx[/yellow]")
            return False
        except Exception as e:
            console.print(f"  [red]Sync failed: {e}[/red]")
            return False

    # ── Full Pipeline ─────────────────────────────────────

    def run_all(self, skip: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run the complete phonon calculation pipeline.

        Args:
            skip: List of step names to skip.

        Returns:
            Dict with all results.
        """
        skip = skip or []

        console.print("\n[bold magenta]╔════════════════════════════════════════╗")
        console.print("[bold magenta]║   🚀 PhononFlow Full Pipeline            ║")
        console.print(f"[bold magenta]║   Material: {self.config.material.name:<30s} ║")
        console.print(f"[bold magenta]║   Backend:  {self.config.backend.type:<30s} ║")
        console.print("[bold magenta]╚════════════════════════════════════════╝[/bold magenta]\n")

        try:
            if "relax" not in skip:
                self.run_relax()
            if "displace" not in skip:
                self.run_displace()
            if "forces" not in skip:
                self.run_forces()
            if "bands" not in skip:
                self.run_bands()
            if "raman" not in skip:
                self.run_raman()
            if "plot" not in skip:
                self.run_plot()
            if "report" not in skip:
                self.render_report()
            if "sync" not in skip:
                self.sync_knowledge()

            console.print("\n[bold green]✅ Pipeline completed successfully![/bold green]")
        finally:
            self.disconnect()

        return self._results

    # ── Helpers ───────────────────────────────────────────

    def _generate_potcar(self, target_path: str, work_dir: str) -> None:
        """Generate POTCAR from element list."""
        material = self.config.material
        elements = material.potcar_elements

        if not elements:
            raise VASPError("No POTCAR elements specified")

        # Upload individual POTCARs from local
        potcar_dir = material.potcar_dir or self.output_dir / "potcar"
        parts = []
        for elem in elements:
            pot_path = Path(potcar_dir) / elem / "POTCAR"
            if pot_path.exists():
                parts.append(pot_path.read_text())
            else:
                raise VASPError(f"POTCAR not found: {pot_path}")
        content = "".join(parts)
        self.backend.upload_content(content, target_path)

    def _submit_disp_job(self, phonon_dir: str, disp_id: str, mat_name: str) -> str:
        """Submit a single displacement job."""
        work_dir = f"{phonon_dir}/disp-{disp_id}"

        if isinstance(self.backend, HPCSLURMBackend):
            script = self.backend.generate_phonon_slurm_script(
                disp_id=disp_id,
                work_dir=work_dir,
                material_name=mat_name,
            )
            self.backend.upload_content(script, f"{work_dir}/submit.slurm")
            return self.backend.submit_job(script, work_dir, "submit.slurm")
        else:
            raise ValueError("Backend does not support job submission")

    def _download_if_needed(self, remote_path: str, local_path: Path) -> None:
        """Download a file if it doesn't exist locally."""
        if not local_path.exists():
            console.print(f"  Downloading {remote_path}...")
            self.backend.download_file(remote_path, str(local_path))
