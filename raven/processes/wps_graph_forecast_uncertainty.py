from pathlib import Path
from matplotlib import pyplot as plt
from pywps import ComplexInput, ComplexOutput, LiteralInput
from pywps import FORMATS
from pywps import Format
from pywps import Process

from raven.utilities.graphs import forecast, hindcast


class GraphFcstUncertaintyProcess(Process):
    def __init__(self):
        inputs = [ComplexInput('fcst', 'Stream flow forecasts',
                               abstract='Stream flow forecast time series',
                               supported_formats=[FORMATS.NETCDF]),
                 
                  LiteralInput("fcst_var","name of the streamflow variable in fcst",
                               abstract="name of the streamflow variable in fcst",
                               data_type="string",
                               min_occurs=0,
                               max_occurs=1,
                               default='q_sim',
                               ),

                  ComplexInput('qobs', 'Stream flow observation',
                               abstract='Stream flow observation for hindcasting',
                               supported_formats=[FORMATS.NETCDF],
                               min_occurs=0,
                               max_occurs=1,),
                  
                  LiteralInput("qobs_var","name of the streamflow variable in qobs",
                               abstract="name of the streamflow variable in qobs",
                               data_type="string",
                               min_occurs=0,
                               max_occurs=1,
                               default='q_obs',
                               ),
                  ]

        outputs = [
            ComplexOutput('graph_forecasts', 'Figure showing the forecast hydrographs.',
                          abstract="Figure showing the forecast hydrographs",
                          as_reference=True,
                          supported_formats=(Format(mime_type='image/png'),)),
                    ]

        super(GraphFcstUncertaintyProcess, self).__init__(
            self._handler,
            identifier="graph_forecast_uncertainty",
            title="",
            version="1.0",
            abstract="",
            metadata=[],
            inputs=inputs,
            outputs=outputs,
            keywords=[],
            status_supported=True,
            store_supported=True)

    def _handler(self, request, response):
        sim_fn = request.inputs['fcst'][0].file
        fcst_var=request.inputs['fcst_var'][0].data
        # Create and save graphic
       
        if 'qobs' in request.inputs:
            # Then its a hindcast with qobs
            qobs_fn = request.inputs['qobs'][0].file
            qobs_var=request.inputs['qobs_var'][0].data
            fig = hindcast(sim_fn, fcst_var, qobs_fn, qobs_var)
        else:
            fig = forecast(sim_fn, fcst_var)

        fig_fn_fcst = Path(self.workdir) / 'forecast_hydrographs.png'
        fig.savefig(fig_fn_fcst)
        plt.close(fig)

        response.outputs['graph_forecasts'].file = str(fig_fn_fcst)

        return response
