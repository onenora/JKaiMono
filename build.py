from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.config import FontConfig
from src.merge import center_cjk_glyphs, merge_fonts, scale_nerd_icons
from src.utils import update_font_names, verify_glyph_width, verify_glyph_width_non_negative


def load_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from YAML file."""
    if not config_path.is_file():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def get_config_value(yaml_config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Get nested value from config dictionary."""
    val: Any = yaml_config
    for key in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(key)
        if val is None:
            return default
    return val


type FontMetadata = dict[str, str]


def build_single_font(
    style: str,
    base_font_path: Path,
    display_name: str,
    output_dir: Path,
    config: FontConfig,
    metadata: FontMetadata,
    nerd_font_path: Path | None = None,
    cn_font_path: Path | None = None,
    is_single_style: bool = False,
    output_filename: str | None = None,
) -> str:
    """Build a single font variant.

    Args:
        style: Font style (Regular, Bold, etc.)
        base_font_path: Path to base font (e.g. LXGWWenKaiScreen)
        display_name: Display name for the style in font metadata
        output_dir: Output directory
        config: FontConfig object
        metadata: Font metadata dict (author, copyright, description, url, license, license_url)
        nerd_font_path: Optional path to Nerd Font icons
        cn_font_path: Optional path to separate CJK font
        is_single_style: Whether only one style is being built
        output_filename: Optional explicit output filename

    Returns:
        Output file path
    """
    print(f"\nBuilding {config.family_name_compact} ({style})...")

    # Merge fonts
    merged_font = merge_fonts(
        base_font_path=str(base_font_path),
        nerd_font_path=str(nerd_font_path) if nerd_font_path else None,
        cn_font_path=str(cn_font_path) if cn_font_path else None,
        config=config,
    )

    if config.monospace and cn_font_path:
        # Monospace-specific processing for merged CJK
        print("  Scaling NerdFont icons...")
        scale_nerd_icons(merged_font, config)

        print("  Centering CJK glyphs...")
        center_cjk_glyphs(merged_font, config)

    # Determine names and output filename
    if output_filename:
        filename = output_filename if output_filename.endswith(".ttf") else f"{output_filename}.ttf"
        postscript_name = Path(filename).stem
        full_name = (
            config.family_name if is_single_style else f"{config.family_name} {display_name}"
        )
    elif is_single_style:
        filename = f"{config.family_name_compact}.ttf"
        postscript_name = config.family_name_compact
        full_name = config.family_name
    else:
        postscript_name = f"{config.family_name_compact}-{style}"
        filename = f"{postscript_name}.ttf"
        full_name = f"{config.family_name} {display_name}"

    print("  Updating font metadata...")
    update_font_names(
        font=merged_font,
        family_name=config.family_name,
        style_name=display_name,
        full_name=full_name,
        postscript_name=postscript_name,
        version_str=f"Version {config.version}",
        author=metadata.get("author", ""),
        copyright_str=metadata.get("copyright", ""),
        description=metadata.get("description", ""),
        url=metadata.get("url", ""),
        license_desc=metadata.get("license", ""),
        license_url=metadata.get("license_url", ""),
    )

    # Verify glyph widths
    print("  Verifying glyph widths...")
    try:
        if config.monospace:
            verify_glyph_width(
                font=merged_font,
                expected_widths=[0, config.en_width, config.cn_width],
                file_name=postscript_name,
            )
        else:
            verify_glyph_width_non_negative(
                font=merged_font,
                file_name=postscript_name,
            )
    except ValueError as e:
        print(f"  Warning: {e}")

    # Save font
    output_path = output_dir / filename
    merged_font.save(str(output_path))
    merged_font.close()

    print(f"  Saved: {output_path}")
    return str(output_path)


def build_font(
    yaml_config: dict[str, Any],
    args: argparse.Namespace,
    default_fonts_dir: Path | None = None,
    default_output_dir: Path | None = None,
    default_parallel: int | None = None,
) -> None:
    """Build fonts for a configuration entry."""
    styles_config = get_config_value(yaml_config, "styles") or {}
    if not styles_config:
        print("Error: No styles defined in config")
        return

    # Merge config: CLI args > YAML > defaults
    styles_str = (
        args.styles
        or get_config_value(yaml_config, "build", "styles")
        or ",".join(styles_config.keys())
    )
    fonts_dir = (
        args.fonts_dir
        or (
            Path(get_config_value(yaml_config, "fonts_dir"))
            if get_config_value(yaml_config, "fonts_dir")
            else None
        )
        or default_fonts_dir
        or Path("fonts")
    )
    output_dir = (
        args.output_dir
        or (
            Path(get_config_value(yaml_config, "build", "output_dir"))
            if get_config_value(yaml_config, "build", "output_dir")
            else None
        )
        or default_output_dir
        or Path("output/fonts")
    )
    parallel = (
        args.parallel
        if args.parallel is not None
        else get_config_value(
            yaml_config,
            "build",
            "parallel",
            default=default_parallel if default_parallel is not None else 1,
        )
    )

    # Font metadata from config
    family_name = get_config_value(yaml_config, "font", "family_name") or "JKaiMono"
    version = get_config_value(yaml_config, "font", "version") or "1.0"
    monospace = get_config_value(yaml_config, "width", "monospace", default=False)
    en_width = get_config_value(
        yaml_config, "width", "en_width", default=1024 if monospace else 600
    )
    cn_width = get_config_value(
        yaml_config, "width", "cn_width", default=2048 if monospace else 1200
    )
    visual_scale = get_config_value(yaml_config, "width", "visual_scale", default=1.0)
    global_nerd_font = get_config_value(yaml_config, "nerd_font")

    # Font metadata for name table
    metadata = {
        "author": get_config_value(yaml_config, "font", "author") or "",
        "copyright": get_config_value(yaml_config, "font", "copyright") or "",
        "description": get_config_value(yaml_config, "font", "description") or "",
        "url": get_config_value(yaml_config, "font", "url") or "",
        "license": get_config_value(yaml_config, "font", "license") or "",
        "license_url": get_config_value(yaml_config, "font", "license_url") or "",
    }

    # Initialize FontConfig
    config = FontConfig(
        family_name=family_name,
        family_name_compact=family_name,
        version=version,
        monospace=monospace,
        visual_scale=visual_scale,
        en_width=en_width,
        cn_width=cn_width,
    )

    # Parse styles to build
    styles = [s.strip() for s in styles_str.split(",")]
    valid_styles = list(styles_config.keys())

    for style in styles:
        if style not in valid_styles:
            print(f"Error: Invalid style '{style}'. Valid styles: {valid_styles}")
            sys.exit(1)

    # Build font paths and validate
    font_paths: dict[str, dict[str, Any]] = {}
    for style in styles:
        style_cfg = styles_config[style]
        base_font = (
            style_cfg.get("base_font")
            or style_cfg.get("font")
            or style_cfg.get("cn_font")
            or style_cfg.get("en_font")
        )
        cn_font = (
            style_cfg.get("cn_font")
            if style_cfg.get("base_font") and style_cfg.get("cn_font") != base_font
            else None
        )
        nerd_font = style_cfg.get("nerd_font") or global_nerd_font
        display_name = style_cfg.get("display_name", style)
        output_filename = style_cfg.get("output_filename") or style_cfg.get("output_file")

        if not base_font:
            print(f"Error: Style '{style}' must have 'base_font' defined")
            sys.exit(1)

        base_font_path = fonts_dir / base_font
        cn_font_path = (fonts_dir / cn_font) if cn_font else None
        nerd_font_path = (fonts_dir / nerd_font) if nerd_font else None

        if not base_font_path.exists():
            print(f"Error: Base font not found: {base_font_path}")
            sys.exit(1)
        if cn_font_path and not cn_font_path.exists():
            print(f"Error: Chinese font not found: {cn_font_path}")
            sys.exit(1)
        if nerd_font_path and not nerd_font_path.exists():
            print(f"Error: Nerd font not found: {nerd_font_path}")
            sys.exit(1)

        font_paths[style] = {
            "base_font_path": base_font_path,
            "cn_font_path": cn_font_path,
            "nerd_font_path": nerd_font_path,
            "display_name": display_name,
            "output_filename": output_filename,
        }

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nBuilding {config.family_name} v{config.version}")
    print(f"Styles: {', '.join(styles)}")
    print(f"Source: {fonts_dir}")
    print(f"Output: {output_dir}")
    if config.monospace:
        print(f"Width ratio: {config.cn_width}:{config.en_width} (2:1 Monospace)")
    else:
        print("Mode: Proportional / Native metrics (not fixed 2:1 monospace)")
    print("Font mapping:")
    for style in styles:
        paths = font_paths[style]
        print(f"  {style}:")
        print(f"    Base: {paths['base_font_path'].name}")
        if paths["cn_font_path"]:
            print(f"    CN: {paths['cn_font_path'].name}")
        if paths["nerd_font_path"]:
            print(f"    NERD: {paths['nerd_font_path'].name}")

    # Build fonts
    is_single_style = len(styles) == 1

    if parallel <= 1:
        # Sequential build
        for style in styles:
            paths = font_paths[style]
            build_single_font(
                style,
                paths["base_font_path"],
                paths["display_name"],
                output_dir,
                config,
                metadata,
                paths["nerd_font_path"],
                paths["cn_font_path"],
                is_single_style=is_single_style,
                output_filename=paths["output_filename"],
            )
    else:
        # Parallel build
        with ProcessPoolExecutor(max_workers=parallel) as executor:
            futures = {
                executor.submit(
                    build_single_font,
                    style,
                    font_paths[style]["base_font_path"],
                    font_paths[style]["display_name"],
                    output_dir,
                    config,
                    metadata,
                    font_paths[style]["nerd_font_path"],
                    font_paths[style]["cn_font_path"],
                    is_single_style=is_single_style,
                    output_filename=font_paths[style]["output_filename"],
                ): style
                for style in styles
            }

            for future in as_completed(futures):
                style = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"Error building {style}: {e}")
                    raise


def main():
    # Default config path
    default_config_path = Path(__file__).parent / "config.yaml"

    parser = argparse.ArgumentParser(
        description="Build JKaiMono font",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build.py
  python build.py --config config.yaml
  python build.py --styles Regular

Configuration priority: CLI args > config.yaml > defaults
        """,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config_path,
        help=f"Path to config.yaml (default: {default_config_path})",
    )
    parser.add_argument(
        "--styles",
        type=str,
        default=None,
        help="Comma-separated styles to build (default: from config or all)",
    )
    parser.add_argument(
        "--fonts-dir",
        type=Path,
        default=None,
        help="Directory containing source fonts (default: from config or fonts/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: from config or output/fonts/)",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=None,
        help="Number of parallel workers (default: from config or 1)",
    )

    args = parser.parse_args()

    # Load YAML config
    yaml_config = load_config(args.config)

    if "fonts" in yaml_config and isinstance(yaml_config["fonts"], list):
        common_fonts_dir = Path(yaml_config["fonts_dir"]) if yaml_config.get("fonts_dir") else None
        common_output_dir = (
            Path(get_config_value(yaml_config, "build", "output_dir"))
            if get_config_value(yaml_config, "build", "output_dir")
            else None
        )
        common_parallel = get_config_value(yaml_config, "build", "parallel")
        for font_entry in yaml_config["fonts"]:
            build_font(
                font_entry,
                args,
                default_fonts_dir=common_fonts_dir,
                default_output_dir=common_output_dir,
                default_parallel=common_parallel,
            )
    else:
        build_font(yaml_config, args)

    print("\nBuild complete!")


if __name__ == "__main__":
    main()
