from dataclasses import astuple, fields

from pywps import LiteralInput
from ravenpy.models import HBVEC

from raven import config
from raven.processes import RavenProcess

from . import wpsio as wio

# Defaults for this process
params_defaults = HBVEC.Params(
    par_x01=0.05984519,
    par_x02=4.072232,
    par_x03=2.001574,
    par_x04=0.03473693,
    par_x05=0.09985144,
    par_x06=0.506052,
    par_x07=3.438486,
    par_x08=38.32455,
    par_x09=0.4606565,
    par_x10=0.06303738,
    par_x11=2.277781,
    par_x12=4.873686,
    par_x13=0.5718813,
    par_x14=0.04505643,
    par_x15=0.877607,
    par_x16=18.94145,
    par_x17=2.036937,
    par_x18=0.4452843,
    par_x19=0.6771759,
    par_x20=1.141608,
    par_x21=1.024278,
)


params = LiteralInput(
    "params",
    "Comma separated list of model parameters",
    abstract="Parameters: " + ", ".join(f.name for f in fields(params_defaults)),
    data_type="string",
    default=", ".join(map(str, astuple(params_defaults))),
    min_occurs=0,
    max_occurs=config.max_parallel_processes,
)


class RavenHBVECProcess(RavenProcess):
    identifier = "raven-hbv-ec"
    abstract = "HBV-EC hydrological model"
    title = ""
    version = ""
    model_cls = HBVEC
    tuple_inputs = {"params": HBVEC.Params}

    inputs = [
        wio.ts,
        wio.nc_spec,
        params,
        wio.start_date,
        wio.end_date,
        wio.nc_index,
        wio.duration,
        wio.run_name,
        wio.area,
        wio.latitude,
        wio.longitude,
        wio.elevation,
        wio.rain_snow_fraction,
        wio.evaporation,
        wio.ow_evaporation,
    ]
