from importlib.resources import files, as_file
import pytest
import pyvista as pv
import os
import docx

from f4enix.output.plotter import MeshPlotter, Atlas
from f4enix.constants import ITER_Z_LEVELS
import tests.resources.plotter as pkg_res

RESOURCES = files(pkg_res)

# Do not know how to implement the root test without having a
# real path
RESOURCES_PATH = os.path.dirname(os.path.abspath(pkg_res.__file__))


@pytest.fixture
def plotter() -> MeshPlotter:
    with as_file(RESOURCES.joinpath('test1.vtk')) as infile:
        mesh = pv.read(infile)
    with as_file(RESOURCES.joinpath('stl.stl')) as infile:
        stl = pv.read(infile)

    plotter = MeshPlotter(mesh, stl)

    return plotter


class TestMeshPlotter:

    def test_slice_toroidal(self, plotter: MeshPlotter):
        slices = plotter.slice_toroidal(20)
        assert len(slices) == 8

        # Check that they are not empty
        for slice in slices:
            assert slice[1].bounds is not None
            assert slice[2].bounds is not None

    @pytest.mark.parametrize('axis', ['x', 'y', 'z'])
    def test_slice_on_axis(self, plotter: MeshPlotter, axis):
        slices = plotter.slice_on_axis(axis, 3)
        # Check that they are not empty
        for slice in slices:
            assert slice[1].bounds is not None
            assert slice[2].bounds is not None

    def test_plot_slices(self, plotter: MeshPlotter, tmpdir):
        slices = plotter.slice_on_axis('y', 3)
        outpath = tmpdir.mkdir('meshplotter')
        plotter.plot_slices(slices, 'Error', outpath)
        assert len(os.listdir(outpath)) == 3

    def test_slice(self, plotter: MeshPlotter):
        # coordinates are in meters, input in mm
        plotter.mesh = plotter.mesh.scale(0.01, inplace=False)

        plotter.stl.scale(0.01, inplace=True)
        slices = plotter.slice(ITER_Z_LEVELS[:-3])
        # verify that they intersect
        for slice in slices:
            assert slice[-1] is not None
            assert slice[1].bounds is not None


class TestAtlas:

    def test_build_from_root(self, tmpdir):
        # cannot run this test on linux architecture
        name = 'test'
        atlas = Atlas(name=name)
        atlas.build_from_root(os.path.join(RESOURCES_PATH, 'root'))
        outfolder = tmpdir.mkdir('atlas')
        try:
            atlas.save(outfolder)

            # try to open it
            with open(os.path.join(outfolder, name+'.docx'), 'rb') as infile:
                doc = docx.Document(infile)
                assert len(doc.paragraphs) == 15

        except NotImplementedError:
            # cannot be tested if word is not installed
            assert True