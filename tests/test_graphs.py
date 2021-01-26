from importlib import reload

from ravenpy.utilities import graphs

reload(graphs)
import xarray as xr
from ravenpy.utilities.testdata import get_local_testdata

from raven.processes.wps_q_stats import fit, stats


def test_ts_fit_graph():
    fn = get_local_testdata(
        "hydro_simulations/raven-gr4j-cemaneige-sim_hmets-0_Hydrographs.nc"
    )
    ds = xr.open_dataset(fn)

    ts = stats(ds.q_sim, op="max")
    p = fit(ts)

    fig = graphs.ts_fit_graph(ts, p)
    return fig
