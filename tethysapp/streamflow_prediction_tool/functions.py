# -*- coding: utf-8 -*-
#
#  functions.py
#  streamflow_prediction_tool
#
#  Created by Alan D. Snow, 2015-2017
#  License: BSD 3-Clause

import datetime
from glob import glob
from json import dumps as json_dumps
import os
from pytz import utc
import re
from shutil import rmtree

from django.contrib import messages
from django.shortcuts import redirect
import pandas as pd
from sqlalchemy import and_
import xarray

# local import
from .app import StreamflowPredictionTool as app
from .model import GeoServerLayer, Watershed
from spt_dataset_manager.dataset_manager import (CKANDatasetManager, 
                                                 GeoServerDatasetManager)


def redirect_with_message(request, url, message, severity="INFO"):
    """
    Redirects to new page with message
    """
    if message not in [m.message for m in messages.get_messages(request)]:
        if severity=="INFO":
            messages.info(request, message)
        elif severity=="WARNING":
            messages.warning(request, message)
        elif severity=="ERROR":
            messages.error(request, message)
    return redirect(url)


def delete_from_database(session, object_to_delete):
    """
    This attempts to delete an object from the database
    """
    try:
        session.delete(object_to_delete)
    except Exception:
        pass
    object_to_delete = None


def delete_old_watershed_prediction_files(watershed):
    """
    Removes old watershed prediction files from system if no other watershed has them
    """
    def delete_prediciton_files(watershed_folder_name, local_prediction_files_location):
        """
        Removes predicitons from folder and folder if not empty
        """
        prediciton_folder = os.path.join(local_prediction_files_location, 
                                         watershed_folder_name)
        #remove watersheds subbsasins folders/files
        if watershed_folder_name and \
        local_prediction_files_location and os.path.exists(prediciton_folder):
            
            #remove all prediction files from watershed/subbasin
            try:
                rmtree(prediciton_folder)
            except OSError:
                pass
            
            #remove watershed folder if no other subbasins exist
            try:
                os.rmdir(os.path.join(local_prediction_files_location, 
                                      watershed_folder_name))
            except OSError:
                pass
        
    #initialize session
    session_maker = app.get_persistent_store_database('main_db', as_sessionmaker=True)
    session = session_maker()

    #Remove ECMWF Forecasta
    #Make sure that you don't delete if another watershed is using the
    #same predictions
    num_ecmwf_watersheds_with_forecast  = session.query(Watershed) \
        .filter(
            and_(
                Watershed.ecmwf_data_store_watershed_name == watershed.ecmwf_data_store_watershed_name,
                Watershed.ecmwf_data_store_subbasin_name == watershed.ecmwf_data_store_subbasin_name
            )
        ) \
        .filter(Watershed.id != watershed.id) \
        .count()
    if num_ecmwf_watersheds_with_forecast <= 0:
        ecmwf_rapid_prediction_directory = app.get_custom_setting('ecmwf_forecast_folder')
        delete_prediciton_files("{0}-{1}".format(watershed.ecmwf_data_store_watershed_name,
                                                 watershed.ecmwf_data_store_subbasin_name),
                                ecmwf_rapid_prediction_directory)
    
    session.close()
              

def delete_old_watershed_geoserver_files(watershed):
    """
    Removes old watershed geoserver files from system
    """
    #initialize geoserver manager
    app_instance_id = app.get_custom_setting('app_instance_id')
    geoserver_manager = GeoServerDatasetManager(engine_url=watershed.geoserver.url,
                                                username=watershed.geoserver.username,
                                                password=watershed.geoserver.password,
                                                app_instance_id=app_instance_id)

    #delete layers which need to be deleted
    if watershed.geoserver_drainage_line_layer:
        if watershed.geoserver_drainage_line_layer.uploaded:
            geoserver_manager.purge_remove_geoserver_layer(watershed.geoserver_drainage_line_layer.name)
                                     
    if watershed.geoserver_boundary_layer:
        if watershed.geoserver_boundary_layer.uploaded:
            geoserver_manager.purge_remove_geoserver_layer(watershed.geoserver_boundary_layer.name)
                                     
    if watershed.geoserver_gage_layer:
        if watershed.geoserver_gage_layer.uploaded:
            geoserver_manager.purge_remove_geoserver_layer(watershed.geoserver_gage_layer.name)

    if watershed.geoserver_ahps_station_layer:
        if watershed.geoserver_ahps_station_layer.uploaded:
            geoserver_manager.purge_remove_geoserver_layer(watershed.geoserver_ahps_station_layer.name)


def delete_rapid_input_ckan(watershed):
    """
    This function deletes RAPID input on CKAN
    """
    data_store = watershed.data_store
    if 'ckan' == data_store.data_store_type.code_name \
    and watershed.ecmwf_rapid_input_resource_id.strip():
        #get dataset managers
        data_manager = CKANDatasetManager(data_store.api_endpoint,
                                          data_store.api_key,
                                          "ecmwf"
                                          )
        data_manager.dataset_engine.delete_resource(watershed.ecmwf_rapid_input_resource_id)
        watershed.ecmwf_rapid_input_resource_id = ""


def delete_old_watershed_files(watershed, ecmwf_local_prediction_files_location):
    """
    Removes old watershed files from system
    """
    #remove old geoserver files
    delete_old_watershed_geoserver_files(watershed)
    #remove old ECMWF prediction files
    delete_old_watershed_prediction_files(watershed)
    #remove RAPID input files on CKAN
    delete_rapid_input_ckan(watershed)


def ecmwf_find_most_current_files(path_to_watershed_files, start_folder):
    """""
    Finds the current output from downscaled ECMWF forecasts
    """""
    if start_folder == "most_recent":
        if not os.path.exists(path_to_watershed_files):
            return None, None
        directories = sorted([d for d in os.listdir(path_to_watershed_files) \
                             if os.path.isdir(os.path.join(path_to_watershed_files, d))],
                             reverse=True)
    else:
        directories = [start_folder]
    for directory in directories:
        try:
            date = datetime.datetime.strptime(directory.split(".")[0],"%Y%m%d")
            time = directory.split(".")[-1]
            path_to_files = os.path.join(path_to_watershed_files, directory)
            if os.path.exists(path_to_files):
                basin_files = sorted(glob(os.path.join(path_to_files,"*.nc")), reverse=True)
                if len(basin_files)>0:
                    hour = int(time)/100
                    return basin_files, (date + datetime.timedelta(0,int(hour)*60*60)).replace(tzinfo=utc)
        except Exception as ex:
            print(ex)
            pass
    # there are no files found
    return None, None


def ecmwf_get_valid_forecast_folder_list(main_watershed_forecast_folder, file_extension):
    """
    Retreives a list of valid forecast forlders for the watershed
    """    
    directories = sorted([d for d in os.listdir(main_watershed_forecast_folder) \
                        if os.path.isdir(os.path.join(main_watershed_forecast_folder, d))],
                         reverse=True)
    output_directories = []
    directory_count = 0
    for directory in directories:
        date = datetime.datetime.strptime(directory.split(".")[0],"%Y%m%d")
        hour = int(directory.split(".")[-1])/100
        path_to_files = os.path.join(main_watershed_forecast_folder, directory)
        if os.path.exists(path_to_files):
            basin_files = glob(os.path.join(path_to_files,"*{0}".format(file_extension)))
            #only add directory to the list if valid                                    
            if len(basin_files) >0:
                output_directories.append({
                    'id' : directory, 
                    'text' : str(date + datetime.timedelta(hours=int(hour)))
                })
                directory_count += 1
            #limit number of directories
            if(directory_count>64):
                break                
    return output_directories


def ecmwf_get_forecast_statistics(forecast_nc_list, river_id, return_data=""):
    """
    Returns the statistics for the 52 member forecast
    """
    # combine 52 ensembles
    qout_datasets = []
    ensemble_index_list = []
    for forecast_nc in forecast_nc_list:
        ensemble_index_list.append(
            int(os.path.basename(forecast_nc)[:-3].split("_")[-1])
        )
        qout_datasets.append(
            xarray.open_dataset(forecast_nc, autoclose=True) \
                .sel(rivid=river_id).Qout
        )

    merged_ds = xarray.concat(qout_datasets,
                              pd.Index(ensemble_index_list, name='ensemble'))

    return_dict = {}
    if return_data == 'high_res' or not return_data:
        # extract the high res ensemble & time
        try:
            return_dict['high_res'] = merged_ds.sel(ensemble=52).dropna('time')
        except IndexError:
            pass

    if return_data != 'high_res' or not return_data:
        # analyze data to get statistic bands
        merged_ds = merged_ds.dropna('time')

        if return_data == 'mean' or 'std' in return_data or not return_data:
            return_dict['mean'] = merged_ds.mean(dim='ensemble')
            std_ar = merged_ds.std(dim='ensemble')
            if return_data == 'std_dev_range_upper' or not return_data:
                return_dict['std_dev_range_upper'] = return_dict['mean'] + std_ar
            if return_data == 'std_dev_range_lower' or not return_data:
                return_dict['std_dev_range_lower'] = return_dict['mean'] - std_ar
        if return_data == "outer_range_lower" or not return_data:
            return_dict['min'] = merged_ds.min(dim='ensemble')
        if return_data == "outer_range_upper" or not return_data:
            return_dict['max'] = merged_ds.max(dim='ensemble')

    return return_dict

def format_name(string):
    """
    Formats watershed name for code
    """
    if string:
        formatted_string = string.strip().replace(" ", "_").lower()
        formatted_string = re.sub(r'[^a-zA-Z0-9_-]', '', formatted_string)
        while formatted_string.startswith("-") or formatted_string.startswith("_"):
            formatted_string = formatted_string[1:]
    else:
        formatted_string = ""
    return formatted_string


def format_watershed_title(watershed, subbasin):
    """
    Formats title for watershed in navigation
    """
    max_length = 30
    watershed = watershed.strip()
    subbasin = subbasin.strip()
    watershed_length = len(watershed)
    if(watershed_length>max_length):
        return watershed[:max_length-1].strip() + "..."
    max_length -= watershed_length
    subbasin_length = len(subbasin)
    if(subbasin_length>max_length):
        return (watershed + " (" + subbasin[:max_length-3].strip() + " ...)")
    return (watershed + " (" + subbasin + ")")


def handle_uploaded_file(f, file_path, file_name):
    """
    Uploads file to specified path
    """
    #remove old file if exists
    try:
        os.remove(os.path.join(file_path, file_name))
    except OSError:
        pass
    #make directory
    if not os.path.exists(file_path):
        os.mkdir(file_path)
    #upload file    
    with open(os.path.join(file_path,file_name), 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def upload_geoserver_layer(geoserver_manager, resource_name, 
                           shp_file_list, geoserver_layer):
    """
    Upload a geoserver layer and return associated result
    """
    layer_name, layer_info = geoserver_manager.upload_shapefile(resource_name, 
                                                                shp_file_list)
    if layer_name and layer_info:
        geoserver_layer.name = layer_name.strip()
        geoserver_layer.uploaded = True
        raw_latlon_bbox = layer_info['latlon_bbox'][:4]
        latlon_bbox=json_dumps([raw_latlon_bbox[0],raw_latlon_bbox[2],
                                raw_latlon_bbox[1],raw_latlon_bbox[3]])
        geoserver_layer.latlon_bbox = latlon_bbox
        geoserver_layer.projection = layer_info['projection']
        geoserver_layer.attribute_list = json_dumps(layer_info['attributes'])
        geoserver_layer.wfs_url = layer_info['wfs']['geojson']
    else:
        raise Exception("Problems uploading {}".format(resource_name))


def update_geoserver_layer_information(geoserver_manager, geoserver_layer):
    """
    Update information about geoserver layer
    """
    layer_info = geoserver_manager.dataset_engine.get_resource(resource_id=geoserver_layer.name)
        
    if layer_info['success']:
        raw_latlon_bbox = layer_info['result']['latlon_bbox'][:4]
        latlon_bbox=json_dumps([raw_latlon_bbox[0],raw_latlon_bbox[2],
                                raw_latlon_bbox[1],raw_latlon_bbox[3]])
        geoserver_layer.latlon_bbox = latlon_bbox
        geoserver_layer.projection = layer_info['result']['projection']
        geoserver_layer.attribute_list = json_dumps(layer_info['result']['attributes'])
        geoserver_layer.wfs_url = layer_info['result']['wfs']['geojson']
    else:
        raise Exception("Problems uploading {0}: {1} ...".format(geoserver_layer.name, 
                                                             layer_info['error']))


def update_geoserver_layer_group_information(geoserver_manager, geoserver_layer):
    """
    Update information about geoserver layer
    """
    layer_info = geoserver_manager.dataset_engine.get_layer_group(geoserver_layer.name)
        
    if layer_info['success']:
        raw_latlon_bbox = layer_info['result']['bounds'][:4]
        if (abs(float(raw_latlon_bbox[0])-float(raw_latlon_bbox[2]))>0.001 and\
            abs(float(raw_latlon_bbox[1])-float(raw_latlon_bbox[3]))>0.001):
            latlon_bbox=json_dumps([raw_latlon_bbox[0],raw_latlon_bbox[2],
                                    raw_latlon_bbox[1],raw_latlon_bbox[3]])
            geoserver_layer.latlon_bbox = latlon_bbox
            geoserver_layer.projection = layer_info['result']['bounds'][-1]
        else:
            raise Exception("Layer group ({0}) has invalid bounding box ...".format(geoserver_layer.name))
    else:
        raise Exception("Problems uploading {0}: {1} ...".format(geoserver_layer.name, 
                                                             layer_info['error']))


def update_geoserver_layer(geoserver_layer, geoserver_layer_name, shp_file,
                           geoserver_manager, session, layer_required=False,
                           is_layer_group=False):
    """
    This function performs the geoserver layer update based on ajax request
    """
    
    geoserver_layer_name = "" if not geoserver_layer_name else geoserver_layer_name.strip()
    #ADD NEW SHAPEFILE TO GEOSERVER
    if shp_file and not is_layer_group:
        #remove old geoserver layer
        if geoserver_layer and geoserver_layer.uploaded:
            geoserver_manager.purge_remove_geoserver_layer(geoserver_layer.name)
            
        if not geoserver_layer:
            #create new layer in database
            geoserver_layer = GeoServerLayer(name="")
            
        #upload shapefile
        upload_geoserver_layer(geoserver_manager, 
                               geoserver_layer_name,
                               shp_file,
                               geoserver_layer)
                               
    #CONNECT TO EXISTING LAYER ON GEOSERVER
    elif geoserver_layer_name:
        if geoserver_layer:
            #if the name of the layer changed, and was previously uploaded, 
            #delete from geoserver
            if geoserver_layer_name != geoserver_layer.name:
                if geoserver_layer.uploaded and not is_layer_group:
                    geoserver_manager.purge_remove_geoserver_layer(geoserver_layer.name)
                geoserver_layer.name = geoserver_layer_name
                geoserver_layer.uploaded = False
        else:
            #create new layer in database
            geoserver_layer = GeoServerLayer(name=geoserver_layer_name)
                
    #REMOVE LAYER FROM GEOSERVER AND DATABASE
    elif not geoserver_layer_name and geoserver_layer and not layer_required:
        if geoserver_layer.uploaded:
            geoserver_manager.purge_remove_geoserver_layer(geoserver_layer.name)
        delete_from_database(session, geoserver_layer)
        geoserver_layer = None
        
    #UPDATE LAYER INFORMATION
    if geoserver_layer and not shp_file:
        if is_layer_group:
            update_geoserver_layer_group_information(geoserver_manager, geoserver_layer)
        else:
            update_geoserver_layer_information(geoserver_manager, geoserver_layer)
    return geoserver_layer


def user_permission_test(user):
    """
    User needs to be superuser or staff
    """
    return user.is_superuser or user.is_staff