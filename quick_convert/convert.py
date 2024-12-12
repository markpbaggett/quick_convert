import subprocess
from pathlib import Path
from tqdm import tqdm
import click
from PIL import Image
import tifftools


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

    def create_pyramidal(self, levels=5):
        Image.MAX_IMAGE_PIXELS = None
        img = Image.open(self.input)

        # Save the first (original) image at full resolution
        img.save(self.output, save_all=True)

        # Generate downsampled images and append them to the TIFF
        width, height = img.size
        for i in range(1, levels):
            # Reduce the image size by half for each level
            img_resized = img.resize((width // (2 ** i), height // (2 ** i)), Image.LANCZOS)

            # Append the resized image to the existing TIFF
            img_resized.save(self.output, save_all=True, append_images=[img_resized])
        return

    def create_pyramidal_complex(self):
        # @TODO: WIP
        Image.MAX_IMAGE_PIXELS = None
        img = Image.open(self.input)
        images = []
        images.append(img)
        for scale in [0.5, 0.25, 0.125]:
            img_resized = img.resize(
                (int(img.width * scale), int(img.height * scale)),
                Image.Resampling.LANCZOS
            )
            images.append(img_resized)
        images[0].save(
            self.output,
            save_all=True,
            append_images=images[1:],
            compression='tiff_lzw'
        )
        info = tifftools.read_tiff(self.output)
        info['ifds'][0]['tags'][tifftools.constants.TileWidth] = (256,)
        info['ifds'][0]['tags'][tifftools.constants.TileLength] = (256,)
        tifftools.write_tiff(info, self.output)


@click.group()
def cli() -> None:
    pass


@cli.command("path", help="Convert files in a path to a specific format.")
@click.option(
    "--type",
    "-t",
    type=click.Choice(["htj2k", "jp2", "pyramidal"], case_sensitive=False),
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
    default=False,
    help="Enable lossless compression. If not provided, lossy compression will be used."
)
@click.option(
    "--output",
    "-o",
    default="output",
    help="Path to the output directory.",
)
def path_command(path: str, type: str, lossless: bool, output: str) -> None:
    """Process all files in the given directory recursively."""
    path_obj = Path(path)
    path_out = Path(output)
    if not path_obj.exists() or not path_obj.is_dir():
        print("Invalid input path provided.")
        return

    # Create output directory if it does not exist
    path_out.mkdir(parents=True, exist_ok=True)

    for file_path in tqdm(path_obj.rglob("*.tif"), desc="Processing files"):
        try:
            # Maintain the directory structure
            relative_path = file_path.relative_to(path_obj)
            output_file = path_out / relative_path.with_suffix("")
            output_file.parent.mkdir(parents=True, exist_ok=True)

            compressor = Compress(str(file_path), str(output_file))

            if type == "htj2k":
                compressor.make_htj2k(lossless=lossless)
            elif type == "jp2":
                compressor.make_jp2(lossless=lossless)
            elif type == "pyramidal":
                compressor.output = str(output_file) + "_pyramidal.tif"
                compressor.create_pyramidal(levels=5)

        except Exception as e:
            print(f"Error processing file {file_path}: {e}")


if __name__ == "__main__":
    cli()
