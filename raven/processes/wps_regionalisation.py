import json
import logging
import string
import traceback
from pathlib import Path

from pywps import FORMATS, ComplexInput, LiteralInput
from pywps.app.exceptions import ProcessError
from ravenpy.utilities import read_gauged_params, read_gauged_properties, regionalize

from . import wpsio as wio
from .wps_raven import RavenProcess

LOGGER = logging.getLogger("PYWPS")


class RegionalisationProcess(RavenProcess):
    """
    Notes
    -----
    The available regionalization methods are:

    .. glossary::

        Multiple linear regression (MLR)
            Ungauged catchment parameters are estimated individually by a linear regression
            against catchment properties.

        Spatial proximity (SP)
            The ungauged hydrograph is an average of the `n` closest catchments' hydrographs.

        Physical similarity (PS)
            The ungauged hydrograph is an average of the `n` most similar catchments' hydrographs.

        Spatial proximity with inverse distance weighting (SP_IDW)
            The ungauged hydrograph is an average of the `n` closest catchments' hydrographs, but
            the average is weighted using inverse distance weighting

        Physical similarity with inverse distance weighting (PS_IDW)
            The ungauged hydrograph is an average of the `n` most similar catchments' hydrographs, but
            the average is weighted using inverse distance weighting

        Spatial proximity with IDW and regression-based augmentation (SP_IDW_RA)
            The ungauged hydrograph is an average of the `n` closest catchments' hydrographs, but
            the average is weighted using inverse distance weighting. Furthermore, the method uses the CANOPEX/USGS
            dataset to estimate model parameters using Multiple Linear Regression. Parameters whose regression r-squared
            is higher than 0.5 are replaced by the MLR-estimated value.

        Physical Similarity with IDW and regression-based augmentation (PS_IDW_RA)
            The ungauged hydrograph is an average of the `n` most similar catchments' hydrographs, but
            the average is weighted using inverse distance weighting. Furthermore, the method uses the CANOPEX/USGS
            dataset to estimate model parameters using Multiple Linear Regression. Parameters whose regression r-squared
            is higher than 0.5 are replaced by the MLR-estimated value.

    """

    identifier = "regionalisation"
    title = "Simulate streamflow at an ungauged site based on surrounding or similar gauged catchments."
    abstract = "Compute the hydrograph for an ungauged catchment using a regionalization method."
    version = "0.1"

    method = LiteralInput(
        "method",
        "Regionalisation method",
        abstract="""
    Regionalisation method to use, one of MLR, SP, PS, SP_IDW,
    PS_IDW, SP_IDW_RA, PS_IDW_RA.

    The available regionalization methods are:

        Multiple linear regression (MLR)
            Ungauged catchment parameters are estimated individually by a linear regression
            against catchment properties.

        Spatial proximity (SP)
            The ungauged hydrograph is an average of the `n` closest catchments' hydrographs.

        Physical similarity (PS)
            The ungauged hydrograph is an average of the `n` most similar catchments' hydrographs.

        Spatial proximity with inverse distance weighting (SP_IDW)
            The ungauged hydrograph is an average of the `n` closest catchments' hydrographs, but
            the average is weighted using inverse distance weighting

        Physical similarity with inverse distance weighting (PS_IDW)
            The ungauged hydrograph is an average of the `n` most similar catchments' hydrographs, but
            the average is weighted using inverse distance weighting

        Spatial proximity with IDW and regression-based augmentation (SP_IDW_RA)
            The ungauged hydrograph is an average of the `n` closest catchments' hydrographs, but
            the average is weighted using inverse distance weighting. Furthermore, the method uses the CANOPEX/USGS
            dataset to estimate model parameters using Multiple Linear Regression. Parameters whose regression r-squared
            is higher than 0.5 are replaced by the MLR-estimated value.

        Physical Similarity with IDW and regression-based augmentation (PS_IDW_RA)
            The ungauged hydrograph is an average of the `n` most similar catchments' hydrographs, but
            the average is weighted using inverse distance weighting. Furthermore, the method uses the CANOPEX/USGS
            dataset to estimate model parameters using Multiple Linear Regression. Parameters whose regression r-squared
            is higher than 0.5 are replaced by the MLR-estimated value.

    """,
        data_type="string",
        allowed_values=(
            "MLR",
            "SP",
            "PS",
            "SP_IDW",
            "PS_IDW",
            "SP_IDW_RA",
            "PS_IDW_RA",
        ),
        default="SP_IDW",
        min_occurs=0,
    )

    ndonors = LiteralInput(
        "ndonors",
        "Number of gauged catchments to use for the regionalizaion.",
        abstract="Number of close or similar catchments to use to generate the representative "
        "hydrograph at the ungauged site.",
        data_type="integer",
        default=5,
        min_occurs=0,
    )

    min_NSE = LiteralInput(
        "min_NSE",
        "NSE Score (unitless)",
        abstract="Minimum calibration NSE value required to be considered in the regionalization.",
        data_type="float",
        default=0.6,
        min_occurs=0,
    )

    properties = ComplexInput(
        "properties",
        "Regionalization properties",
        abstract="json string storing dictionary of properties. The available properties are: "
        "area (km2), longitude (dec.degrees), latitude (dec. degrees), gravelius, perimeter (m), "
        "elevation (m), slope(%), aspect, forest (%), grass (%), wetland (%), water (%), "
        "urban (%), shrubs (%), crops (%) and snowIce (%).",
        min_occurs=1,
        max_occurs=1,
        supported_formats=[
            FORMATS.JSON,
        ],
    )

    inputs = [
        wio.ts,
        wio.start_date,
        wio.end_date,
        wio.latitude,
        wio.longitude,
        wio.rain_snow_fraction,
        wio.nc_spec,
        wio.model_name,
        ndonors,
        min_NSE,
        method,
        properties,
        wio.area,
        wio.elevation,
    ]

    outputs = [wio.hydrograph, wio.ensemble]

    def _handler(self, request, response):
        ts = [e.file for e in request.inputs.pop("ts")]
        model_name = request.inputs.pop("model_name")[0].data
        method = request.inputs.pop("method")[0].data
        ndonors = request.inputs.pop("ndonors")[0].data
        min_NSE = request.inputs.pop("min_NSE")[0].data
        properties = request.inputs.pop("properties")[0].data
        properties = json.loads(properties)

        # TODO: lat and lon from properties could be confused with lat and lon to run model. Should they be the same ?

        kwds = {}
        for spec in request.inputs.pop("nc_spec", []):
            kwds.update(json.loads(spec.data))

        for key, val in request.inputs.items():
            kwds[key] = request.inputs[key][0].data

        response.update_status("Inputs are read", 1)

        nash, params = read_gauged_params(model_name)
        response.update_status("Gauged params are read", 2)

        props = read_gauged_properties(properties.keys())
        ungauged_props = {key: properties[key] for key in properties}
        response.update_status("Gauged properties are read", 3)

        try:
            qsim, ensemble = regionalize(
                method,
                model_name,
                nash,
                params,
                props,
                ungauged_props,
                size=ndonors,
                min_NSE=min_NSE,
                ts=ts,
                **kwds,
            )
        except Exception as exc:
            LOGGER.exception(exc)
            err_msg = traceback.format_exc()
            # By default the error message is limited to 300 chars and strips
            # many special characters
            raise ProcessError(
                err_msg, max_length=len(err_msg), allowed_chars=string.printable
            ) from exc

        response.update_status("Computed regionalization", 99)

        # Write output
        nc_qsim = Path(self.workdir) / "qsim.nc"
        qsim.to_netcdf(nc_qsim)
        response.outputs["hydrograph"].file = str(nc_qsim)

        # TODO: Complete attributes
        nc_ensemble = Path(self.workdir) / "ensemble.nc"
        ensemble.to_netcdf(nc_ensemble)
        response.outputs["ensemble"].file = str(nc_ensemble)

        return response
