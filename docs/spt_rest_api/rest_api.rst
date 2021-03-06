************
SPT REST API
************

A REST API is a web service or a set of methods that can be used to produce or access data without a web interface.
REST APIs use the http protocol to request data. Parameters are passed through a URL using a predetermined organization.
A REST API has been developed to provide access to the Streamflow Prediction Tool (SPT) forecasts without the need to
access the web app interface. This type of service facilitates integration of the SPT with third party web apps, and
the automation of forecast retrievals using programing languages like Python, or R. The available methods and a
description of how to use them are shown below.

GetWaterML for Forecasts Statistics
===================================

+----------------+--------------------------------------------------+---------------+
| Parameter      | Description                                      | Example       |
+================+==================================================+===============+
| watershed_name | The name of watershed or main area of interest.  | Nepal         |
+----------------+--------------------------------------------------+---------------+
| subbasin_name  | The name of the sub basin or sub area.           | Central       |
+----------------+--------------------------------------------------+---------------+
| reach_id       | The identifier for the stream reach.             | 5             |
+----------------+--------------------------------------------------+---------------+
| start_folder   | The date of the forecast (YYYYMMDD.HHHH) [*]_.   | 20170110.1200 |
+----------------+--------------------------------------------------+---------------+
|                | The selected forecast statistic. (high_res, mean,|               |
|                |                                                  |               |
| stat_type      | std_dev_range_upper, std_dev_range_lower,        | mean          |
|                |                                                  |               |
|                | outer_range_upper, outer_range_lower).           |               |
+----------------+--------------------------------------------------+---------------+
.. [*] start_folder=most_recent will retrieve the most recent date available.

Example
-------

>>> import requests
>>> res = requests.get('https://[HOST_Portal]/apps/streamflow-prediction-tool/api/GetWaterML/?watershed_name=Nepal&subbasin_name=Central&reach_id=5&start_folder=most_recent&stat_type=mean', headers={'Authorization': 'Token asdfqwer1234'})

GetHistoricData (1980 - Present)
================================

+----------------+--------------------------------------------------+---------------+
| Parameter      | Description                                      | Example       |
+================+==================================================+===============+
| watershed_name | The name of watershed or main area of interest.  | Nepal         |
+----------------+--------------------------------------------------+---------------+
| subbasin_name  | The name of the sub basin or sub area.           | Central       |
+----------------+--------------------------------------------------+---------------+
| reach_id       | The identifier for the stream reach.             | 5             |
+----------------+--------------------------------------------------+---------------+

Example
-------
>>> import requests
>>> res = requests.get('https://[HOST_Portal]/apps/streamflow-prediction-tool/api/GetHistoricData/?watershed_name=Nepal&subbasin_name=Central&reach_id=5', headers={'Authorization': 'Token asdfqwer1234'})

GetReturnPeriods (2, 10, 20, and 35 year return)
================================================

+----------------+--------------------------------------------------+---------------+
| Parameter      | Description                                      | Example       |
+================+==================================================+===============+
| watershed_name | The name of watershed or main area of interest.  | Nepal         |
+----------------+--------------------------------------------------+---------------+
| subbasin_name  | The name of the sub basin or sub area.           | Central       |
+----------------+--------------------------------------------------+---------------+
| reach_id       | The identifier for the stream reach.             | 5             |
+----------------+--------------------------------------------------+---------------+

Example
-------
>>> import requests
>>> res = requests.get('https://[HOST_Portal]/apps/streamflow-prediction-tool/api/GetReturnPeriods/?watershed_name=Nepal&subbasin_name=Central&reach_id=5', headers={'Authorization': 'Token asdfqwer1234'})

GetAvailableDates
=================

+----------------+--------------------------------------------------+---------------+
| Parameter      | Description                                      | Example       |
+================+==================================================+===============+
| watershed_name | The name of watershed or main area of interest.  | Nepal         |
+----------------+--------------------------------------------------+---------------+
| subbasin_name  | The name of the sub basin or sub area.           | Central       |
+----------------+--------------------------------------------------+---------------+
| reach_id       | The identifier for the stream reach.             | 5             |
+----------------+--------------------------------------------------+---------------+

Example
-------
>>> import requests
>>> res = requests.get('https://[HOST_Portal]/apps/streamflow-prediction-tool/api/GetAvailableDates/?watershed_name=Nepal&subbasin_name=Central&reach_id=5', headers={'Authorization': 'Token asdfqwer1234'})

GetWatersheds
=============

This method takes no parameters and returns a list of the available watersheds.

Example
-------
>>> import requests
>>> res = requests.get('https://[HOST_Portal]/apps/streamflow-prediction-tool/api/GetWatersheds/', headers={'Authorization': 'Token asdfqwer1234'})

GetWarningPoints
================

+----------------+--------------------------------------------------+---------------+
| Parameter      | Description                                      | Example       |
+================+==================================================+===============+
| watershed_name | The name of watershed or main area of interest.  | Nepal         |
+----------------+--------------------------------------------------+---------------+
| subbasin_name  | The name of the sub basin or sub area.           | Central       |
+----------------+--------------------------------------------------+---------------+
| reach_id       | The identifier for the stream reach.             | 5             |
+----------------+--------------------------------------------------+---------------+
| return_period  | The return period that the warning is based on   | (2,10, or 20) |
+----------------+--------------------------------------------------+---------------+
| start_folder   | The date of the forecast (YYYYMMDD.HHHH) [*]_.   | 20170110.1200 |
+----------------+--------------------------------------------------+---------------+

Example
-------
>>> import requests
>>> res = requests.get('https://[HOST_Portal]/apps/streamflow-prediction-tool/api/GetWarningPoints/?watershed_name=nepal&subbasin_name=central&return_period=20&forecast_folder=20170802.0', headers={'Authorization': 'Token asdfqwer1234'})
