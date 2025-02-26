import json
from datetime import datetime as dt
from datetime import timedelta as td

from CoG_repo.src.CoG_config import CoGconfig
CoGcfg = CoGconfig()

# ---------------------------------------------------------
# data

def load_json_file( json_file ):
    with open(json_file, 'r') as f:
        data = json.load(f)
    return data

# ---------------------------------------------------------
# configs

def load_config(cfg='gait'):
    if cfg == 'data':
        from horseconfigs.data_config import DataConfig
        dcfg = DataConfig()
        try:
            dcfg.storage_initialize()
        except:
            print('dcfg.storage_initialize() was executed previously')
        return dcfg
    elif cfg == 'gait':
        from config.gait_config import GaitConfig
        return GaitConfig()
    elif cfg == 'stiffness':
        from config.stiffness_config import StiffnessConfig
        return StiffnessConfig()
    elif cfg == 'CoG':
        return CoGcfg
    else:
        raise Exception('Invalid config type')
    
# ---------------------------------------------------------
# models

def load_models( **kargs ):
    if kargs.get('gcfg', False):
        from horsetoolkit.GaitAnalyzer.prediction import load_models
        return load_models(kargs['gcfg'])
    else:
        return None

# ---------------------------------------------------------
# timestamps

_ts2sec_ = lambda t: dt.strptime(t, CoGcfg.FMT).microsecond*1e-6 + dt.strptime(t, CoGcfg.FMT).second + dt.strptime(t, CoGcfg.FMT).minute*60 + dt.strptime(t, CoGcfg.FMT).hour*3600
ts2sec = lambda ts: [ _ts2sec_(t) for t in ts ]
samples2ts_obj = lambda x, dtime: [(CoGcfg.TS_START+td(seconds=i*dtime)) for i in x]
samples2ts_str = lambda x, dtime: [ts.strftime(CoGcfg.FMT) for ts in samples2ts_obj(x, dtime)]