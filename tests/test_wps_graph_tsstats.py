#!/usr/bin/env python2
"""
Created on Fri May 17 14:02:50 2019

@author: ets
"""

from pywps import Service
from pywps.tests import assert_response_success

from raven.processes import GraphIndicatorAnalysis

from .common import CFG_FILE, client_for, get_output


class TestTimeSeries:
    def test_graph_timeseries_stats(self, get_local_testdata):
        client = client_for(
            Service(processes=[GraphIndicatorAnalysis()], cfgfiles=CFG_FILE)
        )

        datainputs = (
            "ts_stats=files@xlink:href=file://{ts_stats};"
            "trend={trend};"
            "alpha={alpha};".format(
                ts_stats=get_local_testdata("ts_stats_outputs/out.nc"),
                trend=False,
                alpha=0.05,
            )
        )

        resp = client.get(
            service="WPS",
            request="Execute",
            version="1.0.0",
            identifier="ts_stats_graph",
            datainputs=datainputs,
        )

        assert_response_success(resp)
        out = get_output(resp.xml)
        assert out["graph_ts_stats"].endswith(".png")
