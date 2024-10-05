import subprocess
from pathlib import Path
from tqdm import tqdm
import click


class Compress:
    def __init__(self, input: str, output: str) -> None:
        self.input = input
        self.output = output

    def _run_command(self, command: list) -> None:
        """Utility to run a command with subprocess and handle errors."""
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error during compression: {e.stderr}")

    def make_htj2k(self, lossless: bool = True) -> None:
        """Compress to HTJ2K format."""
        base_command = [
            "kdu_compress",
            "-i", self.input,
            "-o", str(Path(self.output).with_suffix(".jph")),
            "Cmodes=HT",
            f"Creversible={'yes' if lossless else 'no'}",
            "ORGgen_plt=yes",
            'Cprecincts={256,256}',
            'Cblk={64,64}',
            "Clevels=8"
        ]

        if not lossless:
            base_command.insert(6, "Qfactor=90")
        self._run_command(base_command)

    def make_jp2(self, lossless: bool = True) -> None:
        """Compress to JP2 format."""
        base_command = [
            "kdu_compress",
            "-i", self.input,
            "-o", str(Path(self.output).with_suffix(".jp2")),
            f"Creversible={'yes' if lossless else 'no'}",
            "ORGgen_plt=yes",
            "Corder=RPCL",
            'Cprecincts={256,256}',
            'Cblk={64,64}',
            "Clevels=8"
        ]

        if not lossless:
            base_command.insert(6, "Qfactor=90")
        print(base_command)
        self._run_command(base_command)


@click.group()
def cli() -> None:
    pass


@cli.command("path", help="Convert files in a path to a specific format.")
@click.option(
    "--type",
    "-t",
    type=click.Choice(["htj2k", "jp2"], case_sensitive=False),
    help="Output file type",
    required=True,
)
@click.option(
    "--path",
    "-p",
    help="Path to the directory containing the files.",
    required=True,
)
@click.option(
    "--lossless",
    "-l",
    is_flag=True,
    show_default=True,
    default=False,  # Default to lossy compression
    help="Enable lossless compression. If not provided, lossy compression will be used."
)
def path_command(path: str, type: str, lossless: bool) -> None:
    """Process all files in the given directory."""
    path_obj = Path(path)

    if not path_obj.exists() or not path_obj.is_dir():
        print("Invalid path provided.")
        return

    for file_path in tqdm(path_obj.rglob("*.tif")):  # Recursively find .tif files
        output_file = file_path.with_suffix("")  # Strip .tif suffix
        compressor = Compress(str(file_path), str(output_file))

        if type == "htj2k":
            compressor.make_htj2k(lossless=lossless)
        elif type == "jp2":
            compressor.make_jp2(lossless=lossless)


if __name__ == "__main__":
    cli()
