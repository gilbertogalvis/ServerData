import json
import numpy as np
import pandas as pd

from horsetoolkit.Data.loader import load_horse_data_from_storage
from horsetoolkit.StiffnessAnalyzer.horseTracker import Tracking

from CoG_repo.src.CoG_utils import load_config, load_models, load_json_file, samples2ts_str
from CoG_repo.src.CoG_processing import do_integral, do_2D_rotation, do_cog_norm_by_gait

class CoG:
    def __init__(self, **kwargs):
        self.training_info = kwargs.get( 'training_info', False )
        print( self.training_info )
        
        self.CoGcfg = kwargs.get( 'CoGcfg', load_config('CoG') )
        self.dcfg = kwargs.get( 'dcfg', load_config('data') )
        self.gcfg = kwargs.get( 'gcfg', load_config('gait') )
        self.scfg = kwargs.get( 'scfg', load_config('stiffness') ); self.scfg.LEGS, self.scfg.SENSORS = [], self.CoGcfg.devices
        
        self.gmodels = load_models( gcfg=self.gcfg )
        # self.tracker = Tracking()
        
        if self.training_info:
            self.load_training_data()
        
            self.do_gait_analysis()
            self.do_IMU_corrections()
        
        self.cog_data = {}
    
    def load_training_data(self, training_info=False):
        self.training_info = training_info if training_info else self.training_info
        self.training_info = self.training_info if isinstance(self.training_info, dict) else load_json_file( self.training_info )
        
        self.dcfg.training_info_to_dict( self.training_info )
        load_horse_data_from_storage( self.dcfg )
        if self.dcfg.no_processing_data(): raise Exception(self.dcfg.message)
        
        self.gcfg.no_nan_index = self.dcfg.no_nan_index
        self.gcfg.nan_index = self.dcfg.nan_index
    
    def do_gait_analysis(self, **kwargs):
        from horsetoolkit.GaitAnalyzer.prediction import get_isolated_gaits
        
        isolated, _, _ = get_isolated_gaits(
            self.dcfg.sensor_data_magnitudes,
            models        =self.gmodels,
            cfg           =self.gcfg,
            use_nan_index =True,
            filename      =None,
        )
        if not isolated['stay'].empty:
            self.dcfg.sensor_data_xyz.loc[isolated['stay']['old_index'].values, :] = 0.0
        
        self.gait = pd.concat([df[['gait']] for g,df in isolated.items()]).loc[
            sorted([
                idx for gait in (gait for gait in isolated if not isolated[gait].empty)
                for idx in isolated[gait]['old_index']
            ])
        ]['gait'].values
    
    def do_IMU_corrections(self):
        self.tracker = Tracking(self.scfg)
        self.tracker.init_data( self.dcfg.sensor_data_xyz, do_filtering=self.scfg.DENOISE, lc=self.scfg.LC )
    
        for device in self.CoGcfg.devices:
            self.tracker.do_IMU_corrections( sen=device )
    
    def do_resampling_data(self, target_fs=10):
        if target_fs == self.cog_data['fs']: return
        
        s_animation = np.round(self.cog_data['fs'] / target_fs, 0).astype( np.intp )
        self.cog_data['fs'] = np.round(self.cog_data['fs']/s_animation, 0)
        
        print( "'fs_animation' teorico: %d | 'fs_animation' real: %d" %(target_fs, self.cog_data['fs']) )
        
        self.cog_data.update( { k:v[::s_animation] for k,v in self.cog_data.items() if isinstance(v, np.ndarray) } )
    
    def do_interval_data(self, interval=False):
        if not interval: return
        
        ts = self.cog_data['ts']
        indices = np.logical_and( ts >= interval[0], ts <= interval[-1] ) if interval else np.ones_like(ts, dtype=bool)
        self.cog_data.update({ k:v[indices] for k,v in self.cog_data.items() if isinstance(v, np.ndarray) })
    
    def init_cog_data(self, fs=False):
        self.cog_data = dict(
            fs=fs if fs else self.tracker.cfg.SAMPLE_RATE
        )
        
    def do_CoG_estimation(self):
        # self.init_cog_data()
        cog_data = {}
        
        for i,device in enumerate(self.CoGcfg.devices):
            # cog_data = dict(fs=self.tracker.cfg.SAMPLE_RATE)
            self.init_cog_data()
            
            self.cog_data.update(
                do_integral( 
                    self.tracker, device=device, level=self.CoGcfg.level, axis=self.CoGcfg.axis, do_norm={'factor':0},
                    filters = dict(
                        # filter_in = self.CoGcfg.filter_in,
                        filter = self.CoGcfg.integral_filters['filter'],
                        filter_out = self.CoGcfg.integral_filters['filter_out'],
                    )
                )
            )
            self.cog_data['yaw' ] = self.tracker.euler[device][:,2].copy()
            self.cog_data['gait'] = self.gait
            # self.cog_data = do_cog_norm_by_gait(self.cog_data, device)
            
            self.do_resampling_data( target_fs=self.CoGcfg.fs_animation )
            self.do_interval_data( interval=self.CoGcfg.interval )

            # if yaw_offset!=0:
            #     raw_offset = do_2D_rotation( raw_cog['x'], raw_cog['y'], np.zeros_like(raw_cog['yaw']) + yaw_offset, as_dict=True )
            #     raw_cog['x'], raw_cog['y'] = raw_offset['x'], raw_offset['y']
            
            cog = do_2D_rotation( self.cog_data['x'], self.cog_data['y'], self.cog_data['yaw'], as_dict=True )
            cog['z'] = self.cog_data['z']
            cog['gait'] = self.cog_data['gait']
            cog = do_cog_norm_by_gait(cog, device, do_norm=self.CoGcfg.do_norm)
            
            # cog_data = self.cog_data.copy()
            cog_data.update(dict(
                fs   = self.cog_data['fs'],
                yaw  = self.cog_data['yaw'],
                gait = self.cog_data['gait'],
                tl   = self.cog_data['ts'],
                ts   = samples2ts_str( self.cog_data['ts']*self.cog_data['fs'], 1.0/self.cog_data['fs'] )
            ))
            cog_data.update(
                {
                    # f'{device.lower().replace("back", "horse")}_raw' : np.array([ self.cog_data['x'], self.cog_data['y'], self.cog_data['z'] ]).T,
                    f'{device.lower().replace("back", "horse")}_cog' : np.array([ cog['x'], cog['y'], cog['z'] ]).T
                }
            )
        
        self.cog_data = cog_data