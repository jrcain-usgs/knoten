from collections import namedtuple
from unittest import mock
import pytest

from plio.io.io_gdal import GeoDataset

import csmapi
from knoten import csm, surface, utils

@pytest.fixture
def mock_dem():
    mock_surface = mock.MagicMock(spec=surface.GdalDem)
    mock_dem = mock.MagicMock(spec=GeoDataset)
    mock_dem.no_data_value = 10
    mock_dem.read_array.return_value = [[100]]
    mock_dem.latlon_to_pixel.return_value = (0.5,0.5)
    mock_surface.dem = mock_dem
    return mock_surface

@pytest.fixture
def mock_sensor():
    mock_sensor = mock.MagicMock(spec=csmapi.RasterGM)
    return mock_sensor

@pytest.fixture
def pt():
    return csmapi.ImageCoord(0.0, 0.0)

def test_generate_ground_point_with_float(mock_sensor):
    csm.generate_ground_point(0, (0.5, 0.5), mock_sensor)
    # The internal conversion from tuple to csmapi.ImageCoord means 
    # assert_called_once_with fails due to different addresses of
    # different objects.
    mock_sensor.imageToGround.assert_called_once()

def test_generate_ground_point_with_imagecoord(mock_sensor, pt):
    height = 0.0
    csm.generate_ground_point(height, pt, mock_sensor)
    mock_sensor.imageToGround.assert_called_once_with(pt, height)

@mock.patch.object(csm, 'get_radii', return_value=(10,10))
@mock.patch.object(csm, '_compute_intersection_distance', return_value=0)
@mock.patch('pyproj.transformer.Transformer.transform', return_value=(0,0,0))
def test_generate_ground_point_with_dtm(mock_get_radii, 
                                        mock_compute_intersection, 
                                        mock_pyproj_transformer, 
                                        mock_sensor, pt, mock_dem):
    csm.generate_ground_point(mock_dem, pt, mock_sensor)
    # This call is mocked so that the intitial intersection and 
    # one iteration should occur. Therefore, the call count
    # should always be 2.
    assert mock_sensor.imageToGround.call_count == 2


@mock.patch.object(csm, 'get_radii', return_value=(10,10))
@mock.patch('pyproj.transformer.Transformer.transform', return_value=(0,0,0))
def test_generate_ground_point_with_dtm_ndv(mock_get_radii,
                                            mock_pyproj_transformer,
                                            mock_sensor, pt, mock_dem):
    mock_dem.get_height.return_value = None
    with pytest.raises(ValueError):
        res = csm.generate_ground_point(mock_dem, pt, mock_sensor)

def test__compute_intersection_distance():
    Point = namedtuple("Point", 'x, y, z')
    pt1 = Point(0,0,0)
    pt2 = Point(1,1,1)
    dist = csm._compute_intersection_distance(pt1, pt2)
    assert dist == 1


def test_get_state(mock_sensor, pt):
    Locus = namedtuple("Locus", 'point direction')

    mock_sensor.getImageTime.return_value = 0.0
    mock_sensor.imageToRemoteImagingLocus.return_value = Locus(utils.Point(0, 1, 2), utils.Point(0, 1, 2))
    mock_sensor.getSensorPosition.return_value = utils.Point(2, 2, 2)

    state = csm.get_state(mock_sensor, pt)

    expected = {
        "lookVec": utils.Point(0, 1, 2),
        "sensorPos": utils.Point(2, 2, 2),
        "sensorTime": 0.0,
        "imagePoint": pt
    }

    assert state == expected


@mock.patch.object(csm, 'get_radii', return_value=(10, 10))
def test_get_surface_normal(mock_sensor):
    ground_pt = utils.Point(1, 0, 0)
    normal = csm.get_surface_normal(mock_sensor, ground_pt)

    assert normal == (1.0, 0.0, 0.0)