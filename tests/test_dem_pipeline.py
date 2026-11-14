"""Synthetic local raster tests for the adapter; NOT NASA science verification."""
import pytest


def test_synthetic_lunar_dem_conversion(tmp_path):
    rasterio = pytest.importorskip('rasterio')
    np = pytest.importorskip('numpy')
    pyproj = pytest.importorskip('pyproj')
    from rasterio.transform import from_origin
    from tools.prepare_lola_horizon import create_profile
    target = pyproj.CRS.from_proj4(
        '+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +a=1737400 +b=1737400 +units=m +no_defs')
    source=pyproj.CRS.from_proj4('+proj=longlat +a=1737400 +b=1737400 +no_defs')
    p=pyproj.Transformer.from_crs(source,target,always_xy=True)
    x,y=p.transform(203.803,-89.7804)
    width=160
    cell=100.0
    output=tmp_path/'fake_lunar_terrain.tif'
    # Terrain heights arbitrary; provenance clearly synthetic.
    heights=np.full((width,width),2000.0,dtype='float32')
    heights[80:83,80:83]+=500.0
    with rasterio.open(output,'w',driver='GTiff',height=width,width=width,count=1,
                       dtype='float32',crs=target,
                       transform=from_origin(x-cell*width/2,y+cell*width/2,cell,cell)) as ds:
        ds.write(heights,1)
    h=create_profile(str(output),-89.7804,203.803,2.0,2.0,45,200)
    assert len(h['elevations_deg'])==8
    assert 'fake_lunar_terrain' in h['provenance']
    assert all(-90<=v<=90 for v in h['elevations_deg'])
