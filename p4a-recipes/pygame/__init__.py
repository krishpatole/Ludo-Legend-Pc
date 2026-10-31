"""Android-specific pygame 2.6.1 recipe for CPython 3.14.

The upstream python-for-android pygame recipe is pinned to pygame 2.1.0,
whose generated C sources include the removed public header longintrepr.h.
This local recipe builds pygame from its GitHub source archive so Cython
regenerates the extension sources against the Python headers in this build.
"""

from pathlib import Path

from pythonforandroid.recipes.pygame import Pygame2Recipe
from pythonforandroid.toolchain import current_directory


class Pygame261Recipe(Pygame2Recipe):
    version = "2.6.1"
    url = "https://github.com/pygame/pygame/archive/{version}.tar.gz"
    hostpython_prerequisites = ["setuptools", "cython>=3.1,<3.2"]

    def prebuild_arch(self, arch):
        # Patch the Android setup template before the upstream recipe turns
        # it into the final Setup file used by pygame's build.
        with current_directory(self.get_build_dir(arch.arch)):
            template_path = Path("buildconfig/Setup.Android.SDL2.in")
            if not template_path.exists():
                raise RuntimeError(
                    "pygame 2.6.1 Android setup template was not found: "
                    f"{template_path}"
                )

            lines = template_path.read_text(encoding="utf-8").splitlines()
            patched_lines = []
            found_surface = False

            for line in lines:
                stripped = line.lstrip()

                # _sprite is optional; pygame.sprite uses the pure-Python
                # implementation and does not need this Cython extension.
                if stripped.startswith("_sprite "):
                    continue

                if stripped.startswith("surface "):
                    found_surface = True
                    if "simd_blitters_sse2.c" not in line:
                        line = line.replace(
                            "surface ",
                            "surface src_c/simd_blitters_sse2.c "
                            "src_c/simd_blitters_avx2.c ",
                            1,
                        )

                patched_lines.append(line)

            if not found_surface:
                raise RuntimeError(
                    "Could not find the pygame surface module line in "
                    "Setup.Android.SDL2.in; refusing an incomplete build."
                )

            template_path.write_text(
                "\n".join(patched_lines) + "\n", encoding="utf-8"
            )

            # Cython 3.1 rejects this optional accelerator's __dict__ use.
            # pygame.sprite does not import it, so omit it from Android.
            sprite_pyx = Path("src_c/cython/pygame/_sprite.pyx")
            if sprite_pyx.exists():
                sprite_pyx.unlink()

        # The upstream recipe now generates its Setup file from our patched
        # Android template and performs its normal SDL2 configuration.
        super().prebuild_arch(arch)


recipe = Pygame261Recipe()
