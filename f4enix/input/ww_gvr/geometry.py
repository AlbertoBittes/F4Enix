from pathlib import Path
from f4enix.input.ww_gvr.meshgrids import create_cartesian_grid, create_cylindrical_grid
from f4enix.input.ww_gvr.models import Vectors, CoordinateType, ValuesByParticle
from f4enix.input.ww_gvr.utils import build_1d_vectors, compose_b2_vectors
from f4enix.input.ww_gvr.ww_parser import WWHeader, WWHeaderCyl


import numpy as np
from numpy.typing import NDArray
import pyvista as pv
from pyvista.plotting.plotter import Plotter as Plotter


from typing import Dict, List


class Geometry:
    def __init__(
        self, header: WWHeader, coarse_vectors: Vectors, fine_vectors: Vectors
    ):
        self._coarse_vectors = coarse_vectors
        self._fine_vectors = fine_vectors

        self._coordinate_type = (
            CoordinateType.CARTESIAN
            if type(header) == WWHeader
            else CoordinateType.CYLINDRICAL
        )

        self._director_1 = header.director_1 if type(header) == WWHeaderCyl else None
        self._director_2 = header.director_2 if type(header) == WWHeaderCyl else None
        self._origin = header.origin

        self._grid = self._create_grid()

    def _create_grid(self) -> pv.StructuredGrid:
        origin = np.array(self.origin)

        if self.coordinate_type == CoordinateType.CARTESIAN:
            return create_cartesian_grid(*self.vectors, origin=origin)

        else:
            vector_i, vector_j, vector_k = self.vectors
            axis = np.array(self.director_1)
            vec = np.array(self.director_2)
            return create_cylindrical_grid(
                vector_i, vector_j, vector_k, origin, axis, vec
            )

    def fill_grid_values(self, values_by_particle: ValuesByParticle) -> None:
        for particle in values_by_particle.keys():
            for energy in values_by_particle[particle].keys():
                values = values_by_particle[particle][energy]
                self.fill_grid_array(values, f"WW {particle}, {energy:.2f} MeV")

    def fill_grid_ratios(self, ratios_by_particle: ValuesByParticle) -> None:
        for particle in ratios_by_particle.keys():
            for energy in ratios_by_particle[particle].keys():
                ratios = ratios_by_particle[particle][energy]
                self.fill_grid_array(ratios, f"Ratio {particle}, {energy:.2f} MeV")

            max_ratios = np.max(list(ratios_by_particle[particle].values()), axis=0)
            self.fill_grid_array(max_ratios, f"Max Ratio {particle}")

    def fill_grid_array(self, array: NDArray, name: str) -> None:
        """Fills the grid with an array given in K, J, I order"""
        if self.coordinate_type == CoordinateType.CYLINDRICAL:
            array = self._prepare_values_for_cylindrical_grid(array)

        flattened_array = array.flatten()
        self._grid[name] = flattened_array

    def _prepare_values_for_cylindrical_grid(self, values: NDArray) -> NDArray:
        # If the grid was extended in the thetas, values should do the same
        total_ints = self.i_ints * self.j_ints * self.k_ints
        extended = self._grid.n_cells // total_ints
        if extended > 1:
            values = np.repeat(values, extended, axis=0)

        # The grids with cylindrical coordinates created with meshgrids.py
        #  have dimensions with the order (j, k, i) instead of (k, j, i)
        values = values.swapaxes(0, 1)

        return values

    @property
    def coordinate_type(self) -> CoordinateType:
        return self._coordinate_type

    @property
    def vectors(self) -> Vectors:
        """Returns a Vectors object (1D) with the coarse and fine vectors combined"""
        return build_1d_vectors(self._coarse_vectors, self._fine_vectors)

    @property
    def b2_vectors(self) -> Vectors:
        return compose_b2_vectors(self._coarse_vectors, self._fine_vectors)

    @property
    def director_1(self) -> List[float] | None:
        return self._director_1

    @property
    def director_2(self) -> List[float] | None:
        return self._director_2

    @property
    def origin(self) -> List[float]:
        return self._origin

    @property
    def i_ints(self) -> int:
        return np.sum(self._fine_vectors.vector_i)

    @property
    def j_ints(self) -> int:
        return np.sum(self._fine_vectors.vector_j)

    @property
    def k_ints(self) -> int:
        return np.sum(self._fine_vectors.vector_k)

    @property
    def i_coarse_ints(self) -> int:
        return len(self._coarse_vectors.vector_i) - 1

    @property
    def j_coarse_ints(self) -> int:
        return len(self._coarse_vectors.vector_j) - 1

    @property
    def k_coarse_ints(self) -> int:
        return len(self._coarse_vectors.vector_k) - 1

    def plot(self) -> None:
        args_dict = self._decide_plot_parameters()
        plotter = Plotter()
        plotter.add_mesh_clip_plane(self._grid, **args_dict)
        plotter.show_grid(color="black")  # type: ignore
        plotter.show_axes()  # type: ignore
        plotter.show()

    def _decide_plot_parameters(self) -> Dict:
        sclar_bar_args = {
            "interactive": True,
            "title_font_size": 20,
            "label_font_size": 16,
            "shadow": True,
            "italic": True,
            "fmt": "%.e",
            "font_family": "arial",
        }
        args_dict = {
            "scalars": self._grid.array_names[0],
            "scalar_bar_args": sclar_bar_args,
            "show_edges": False,
            "cmap": "jet",
            "log_scale": False,
            "lighting": False,
        }

        # Decide about the log scale
        data = np.array(self._grid[args_dict["scalars"]])
        data_max = data.max()
        data_min = data[data != 0].min()
        if data_max / data_min < 1e5:
            args_dict["log_scale"] = False
            return args_dict

        args_dict["log_scale"] = True
        exp_max = int(np.log10(data_max))
        data_max = 10**exp_max
        data_min = 10 ** (exp_max - 10)
        args_dict["clim"] = [data_min, data_max]
        args_dict["n_colors"] = 10
        args_dict["scalar_bar_args"]["n_labels"] = 10

        return args_dict

    def export_as_vtk(self, file_path: Path) -> None:
        if file_path.suffix != ".vts":
            file_path = file_path.with_suffix(".vts")

        self._grid.save(str(file_path))